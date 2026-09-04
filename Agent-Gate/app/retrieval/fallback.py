"""Graceful degradation wrapper: retrieval unavailable -> local scenario catalog only.

Never claims full semantic coverage when the fallback path was used — callers
must set semantic_coverage_degraded on the run/report whenever `degraded` is True.
"""

from dataclasses import dataclass
from typing import Any, Protocol

from app.retrieval.pinecone_client import EmbeddingUnavailableError, PineconeUnavailableError

# Both failure modes degrade retrieval the same way from the caller's
# perspective, but are recorded under different InfraIssue.kind values so a
# run/report points at the system actually at fault (OpenAI vs. Pinecone)
# instead of always blaming Pinecone.
SEMANTIC_DEGRADATION_KINDS = frozenset({"pinecone_degraded", "embedding_unavailable"})


class Retriever(Protocol):
    def query(
        self, *, tenant_id: str, query_text: str, doc_type: str | None = None, top_k: int = 5
    ) -> list[dict[str, Any]]: ...


@dataclass
class RetrievalOutcome:
    results: list[dict[str, Any]]
    degraded: bool
    reason: str | None = None
    kind: str = "pinecone_degraded"


def retrieve_with_fallback(
    retriever: Retriever, *, tenant_id: str, query_text: str, doc_type: str | None = None, top_k: int = 5
) -> RetrievalOutcome:
    try:
        results = retriever.query(tenant_id=tenant_id, query_text=query_text, doc_type=doc_type, top_k=top_k)
        return RetrievalOutcome(results=results, degraded=False)
    except EmbeddingUnavailableError as exc:
        return RetrievalOutcome(results=[], degraded=True, reason=str(exc), kind="embedding_unavailable")
    except PineconeUnavailableError as exc:
        return RetrievalOutcome(results=[], degraded=True, reason=str(exc), kind="pinecone_degraded")
