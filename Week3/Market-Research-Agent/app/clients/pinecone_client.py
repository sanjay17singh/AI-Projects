"""The only module that talks to Pinecone. Every test replaces this with an
in-memory fake implementing the same ensure_index/upsert/query interface."""

from typing import Any

from langsmith import traceable
from pinecone import Pinecone, ServerlessSpec

from app.config import Settings


class PineconeClient:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._pc = Pinecone(api_key=settings.pinecone_api_key)
        self._index = None

    def ensure_index(self) -> None:
        settings = self._settings
        if not self._pc.has_index(settings.pinecone_index_name):
            self._pc.create_index(
                name=settings.pinecone_index_name,
                dimension=settings.pinecone_embedding_dimension,
                metric="cosine",
                spec=ServerlessSpec(cloud=settings.pinecone_cloud, region=settings.pinecone_region),
            )

    def _index_handle(self):
        if self._index is None:
            self._index = self._pc.Index(self._settings.pinecone_index_name)
        return self._index

    @traceable(run_type="tool", name="pinecone_upsert")
    def upsert(
        self, vectors: list[tuple[str, list[float], dict[str, Any]]], namespace: str
    ) -> None:
        """vectors: list of (id, embedding, metadata) triples.

        @traceable is a graceful no-op when LangSmith tracing isn't enabled
        (same no-op philosophy as init_tracing()/init_futureagi_tracing()) —
        when it is enabled, this shows up as a child "tool" span under
        whatever traced call (e.g. an eval run) invoked it, since Pinecone
        calls aren't LangChain Runnables and wouldn't otherwise be traced."""
        payload = [
            {"id": vid, "values": values, "metadata": metadata} for vid, values, metadata in vectors
        ]
        self._index_handle().upsert(vectors=payload, namespace=namespace)

    @traceable(run_type="tool", name="pinecone_query")
    def query(
        self,
        vector: list[float],
        namespace: str,
        top_k: int,
        filter: dict[str, Any],
    ) -> list[dict[str, Any]]:
        result = self._index_handle().query(
            vector=vector, top_k=top_k, filter=filter, namespace=namespace, include_metadata=True
        )
        matches = result.get("matches") if isinstance(result, dict) else result.matches
        out = []
        for m in matches or []:
            metadata = m["metadata"] if isinstance(m, dict) else m.metadata
            score = m["score"] if isinstance(m, dict) else m.score
            out.append({"metadata": metadata, "score": score})
        return out

    def delete_namespace(self, namespace: str) -> None:
        self._index_handle().delete(delete_all=True, namespace=namespace)
