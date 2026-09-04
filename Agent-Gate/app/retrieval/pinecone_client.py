"""Pinecone-backed semantic retrieval — tenant-aware namespaces and metadata.

Pinecone is never the authoritative store for anything security- or
audit-critical: it only serves semantic search over policies, docs, scenario
descriptions, prior failures, regression-test descriptions, and sanitized
evidence summaries. The index is rebuildable from PostgreSQL + the local
scenario catalog at any time.
"""

from typing import Any

from langchain_openai import OpenAIEmbeddings
from pinecone import Pinecone

from app.config import Settings, get_settings

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536  # text-embedding-3-small's default output dimension


class PineconeUnavailableError(Exception):
    """Raised for a Pinecone-side failure — missing credentials, network error,
    index error. Callers (app/retrieval/fallback.py) must catch this and
    degrade, never propagate it as an unhandled crash.
    """


class EmbeddingUnavailableError(Exception):
    """Raised when generating the query/document embeddings fails — this is an
    OpenAI-side failure (missing/invalid key, rate limit, outage), not a
    Pinecone problem, even though it also means retrieval can't proceed.
    Kept distinct from PineconeUnavailableError so an infra_issue on the run
    is labeled with the system actually at fault, not always "pinecone".
    """


class PineconeRetriever:
    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()
        self._client: Pinecone | None = None
        self._index = None
        self._embeddings: OpenAIEmbeddings | None = None

    def namespace_for(self, tenant_id: str) -> str:
        return f"{self._settings.pinecone_namespace_prefix}-{tenant_id}"

    def _ensure_ready(self):
        if not self._settings.pinecone_api_key:
            raise PineconeUnavailableError("PINECONE_API_KEY is not configured")
        if self._index is None:
            try:
                self._client = Pinecone(api_key=self._settings.pinecone_api_key)
                self._index = self._client.Index(self._settings.pinecone_index_name)
                self._embeddings = OpenAIEmbeddings(
                    model=EMBEDDING_MODEL, api_key=self._settings.openai_api_key or "sk-not-configured"
                )
            except Exception as exc:
                self._index = None
                raise PineconeUnavailableError(str(exc)) from exc
        return self._index, self._embeddings

    def upsert_documents(
        self, *, tenant_id: str, doc_type: str, documents: list[dict[str, Any]]
    ) -> None:
        """documents: [{id, text, metadata}]"""
        index, embeddings = self._ensure_ready()
        try:
            vectors = embeddings.embed_documents([d["text"] for d in documents])
        except Exception as exc:
            raise EmbeddingUnavailableError(str(exc)) from exc
        try:
            payload = [
                {
                    "id": d["id"],
                    "values": vector,
                    "metadata": {
                        **d.get("metadata", {}),
                        "doc_type": doc_type,
                        "tenant_id": tenant_id,
                        "text": d["text"],
                    },
                }
                for d, vector in zip(documents, vectors, strict=True)
            ]
            index.upsert(vectors=payload, namespace=self.namespace_for(tenant_id))
        except Exception as exc:
            raise PineconeUnavailableError(str(exc)) from exc

    def query(
        self, *, tenant_id: str, query_text: str, doc_type: str | None = None, top_k: int = 5
    ) -> list[dict[str, Any]]:
        index, embeddings = self._ensure_ready()
        try:
            vector = embeddings.embed_query(query_text)
        except Exception as exc:
            raise EmbeddingUnavailableError(str(exc)) from exc
        try:
            filter_ = {"tenant_id": tenant_id}
            if doc_type:
                filter_["doc_type"] = doc_type
            response = index.query(
                vector=vector,
                top_k=top_k,
                namespace=self.namespace_for(tenant_id),
                filter=filter_,
                include_metadata=True,
            )
            return [
                {"id": m["id"], "score": m["score"], "metadata": m.get("metadata", {})}
                for m in response.get("matches", [])
            ]
        except Exception as exc:
            raise PineconeUnavailableError(str(exc)) from exc
