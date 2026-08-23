"""Hybrid retrieval: Pinecone dense vector search + in-memory BM25 keyword search,
fused with LangChain's EnsembleRetriever (Reciprocal Rank Fusion).

Pinecone is strictly the dense vector store here — BM25 is a separate, in-memory
keyword index built directly from the source knowledge base (not persisted, not
stored in Pinecone). The RRF fusion rank from the ensemble is the retrieval
signal fed to generation, standing in for a separate cross-encoder/Cohere rerank
stage: it is a strictly better confidence signal than raw cosine or BM25 scores
taken alone.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from schemas import RetrievedDoc

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536
DEFAULT_TOP_K = 5


def _split_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("---", 3)
    if end == -1:
        return {}, text
    header = text[3:end].strip()
    body = text[end + 3 :].strip()
    meta = {}
    for line in header.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
    return meta, body


def load_source_documents() -> list[Document]:
    """Load tickets, FAQs, and pricing docs into raw (unchunked) LangChain Documents."""

    docs: list[Document] = []

    with open(DATA_DIR / "tickets.json") as f:
        for t in json.load(f):
            text = (
                f"Subject: {t['subject']}\n"
                f"Customer message: {t['customer_message']}\n"
                f"Resolution: {t['resolution']}"
            )
            metadata = {
                "source_id": t["id"],
                "source_type": "ticket",
                "category": t["category"],
            }
            if t.get("dollar_amount") is not None:
                metadata["dollar_amount"] = t["dollar_amount"]
            docs.append(Document(page_content=text, metadata=metadata))

    with open(DATA_DIR / "faqs.json") as f:
        for entry in json.load(f):
            text = f"Q: {entry['question']}\nA: {entry['answer']}"
            docs.append(
                Document(
                    page_content=text,
                    metadata={
                        "source_id": entry["id"],
                        "source_type": "faq",
                        "category": entry["category"],
                    },
                )
            )

    pricing_dir = DATA_DIR / "pricing_docs"
    for path in sorted(pricing_dir.glob("*.md")):
        raw = path.read_text()
        meta, body = _split_frontmatter(raw)
        docs.append(
            Document(
                page_content=body,
                metadata={
                    "source_id": meta.get("id", path.stem),
                    "source_type": "pricing_doc",
                    "category": meta.get("category", "general_policy"),
                },
            )
        )

    return docs


def chunk_documents(docs: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    chunks = splitter.split_documents(docs)

    # Stable chunk_id (source_id + position), shared by the Pinecone upsert id and the
    # in-memory BM25 corpus, so a chunk found by both retrievers can be matched up for
    # the retrieval-transparency view (dense rank vs. BM25 rank vs. fused rank).
    counts: dict[str, int] = {}
    for chunk in chunks:
        source_id = chunk.metadata.get("source_id", "unknown")
        counts[source_id] = counts.get(source_id, 0) + 1
        chunk.metadata["chunk_id"] = f"{source_id}::{counts[source_id]}"

    return chunks


@lru_cache(maxsize=1)
def get_chunked_documents() -> tuple[Document, ...]:
    return tuple(chunk_documents(load_source_documents()))


@lru_cache(maxsize=1)
def build_bm25_retriever(k: int = DEFAULT_TOP_K):
    from langchain_community.retrievers.bm25 import BM25Retriever

    retriever = BM25Retriever.from_documents(list(get_chunked_documents()))
    retriever.k = k
    return retriever


def _pinecone_index_name() -> str:
    return os.environ.get("PINECONE_INDEX_NAME", "billing-support-bot")


def build_vector_retriever(category: str | None = None, k: int = DEFAULT_TOP_K):
    from langchain_openai import OpenAIEmbeddings
    from langchain_pinecone import PineconeVectorStore

    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
    store = PineconeVectorStore(index_name=_pinecone_index_name(), embedding=embeddings)
    search_kwargs: dict = {"k": k}
    if category:
        search_kwargs["filter"] = {"category": category}
    return store.as_retriever(search_kwargs=search_kwargs)


RRF_C = 60  # matches EnsembleRetriever's default `c` (RRF smoothing constant)
RRF_WEIGHTS = (0.5, 0.5)  # (dense, bm25) — equal weighting, per the hybrid retrieval design


def _rrf_score(dense_rank: int | None, bm25_rank: int | None) -> float | None:
    if dense_rank is None and bm25_rank is None:
        return None
    score = 0.0
    if dense_rank is not None:
        score += RRF_WEIGHTS[0] / (RRF_C + dense_rank)
    if bm25_rank is not None:
        score += RRF_WEIGHTS[1] / (RRF_C + bm25_rank)
    return score


def _to_retrieved_doc(doc: Document, dense_rank: int | None, bm25_rank: int | None) -> RetrievedDoc:
    return RetrievedDoc(
        source_id=doc.metadata.get("source_id", "unknown"),
        source_type=doc.metadata.get("source_type", "faq"),
        category=doc.metadata.get("category", "general_policy"),
        text=doc.page_content,
        chunk_id=doc.metadata.get("chunk_id"),
        dense_rank=dense_rank,
        bm25_rank=bm25_rank,
        rrf_score=_rrf_score(dense_rank, bm25_rank),
    )


def hybrid_search(query: str, category: str | None = None, k: int = DEFAULT_TOP_K) -> dict[str, list[RetrievedDoc]]:
    """Run Pinecone dense retrieval and in-memory BM25 independently, then fuse via RRF.

    Returns {"fused": [...], "dense": [...], "bm25": [...]} — "fused" is what generation
    uses; "dense"/"bm25" are each retriever's own pre-fusion ranking, exposed so the UI can
    show the hybrid mechanics (which retriever(s) found a chunk, at what rank, and its
    resulting RRF score) rather than just the final blended list.
    """

    from langchain_classic.retrievers.ensemble import EnsembleRetriever

    vector_retriever = build_vector_retriever(category=category, k=k)
    bm25_retriever = build_bm25_retriever(k=k)

    dense_docs = vector_retriever.invoke(query)
    bm25_docs = bm25_retriever.invoke(query)

    dense_rank_by_chunk = {d.metadata.get("chunk_id"): i + 1 for i, d in enumerate(dense_docs)}
    bm25_rank_by_chunk = {d.metadata.get("chunk_id"): i + 1 for i, d in enumerate(bm25_docs)}

    def ranks_for(doc: Document) -> tuple[int | None, int | None]:
        chunk_id = doc.metadata.get("chunk_id")
        return dense_rank_by_chunk.get(chunk_id), bm25_rank_by_chunk.get(chunk_id)

    ensemble = EnsembleRetriever(retrievers=[vector_retriever, bm25_retriever], weights=list(RRF_WEIGHTS), c=RRF_C)
    fused_docs = ensemble.invoke(query)[:k]

    return {
        "fused": [_to_retrieved_doc(d, *ranks_for(d)) for d in fused_docs],
        "dense": [_to_retrieved_doc(d, *ranks_for(d)) for d in dense_docs],
        "bm25": [_to_retrieved_doc(d, *ranks_for(d)) for d in bm25_docs],
    }
