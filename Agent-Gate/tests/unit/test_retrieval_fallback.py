from app.config import Settings
from app.retrieval.fallback import retrieve_with_fallback
from app.retrieval.pinecone_client import (
    EmbeddingUnavailableError,
    PineconeRetriever,
    PineconeUnavailableError,
)


class _AlwaysFailsRetriever:
    def query(self, *, tenant_id, query_text, doc_type=None, top_k=5):
        raise PineconeUnavailableError("simulated outage")


class _EmbeddingFailsRetriever:
    def query(self, *, tenant_id, query_text, doc_type=None, top_k=5):
        raise EmbeddingUnavailableError("simulated invalid OpenAI key")


class _WorksRetriever:
    def query(self, *, tenant_id, query_text, doc_type=None, top_k=5):
        return [{"id": "doc-1", "score": 0.9, "metadata": {"text": "policy text"}}]


def test_retrieve_with_fallback_degrades_on_pinecone_unavailable():
    outcome = retrieve_with_fallback(_AlwaysFailsRetriever(), tenant_id="default", query_text="refund policy")
    assert outcome.degraded is True
    assert outcome.results == []
    assert "simulated outage" in outcome.reason
    assert outcome.kind == "pinecone_degraded"


def test_retrieve_with_fallback_labels_embedding_failure_distinctly_from_pinecone():
    """A failed OpenAI embedding call must not be mislabeled as a Pinecone
    problem — they're different systems and a reader diagnosing the run needs
    to know which one to check.
    """
    outcome = retrieve_with_fallback(_EmbeddingFailsRetriever(), tenant_id="default", query_text="refund policy")
    assert outcome.degraded is True
    assert outcome.kind == "embedding_unavailable"
    assert "simulated invalid OpenAI key" in outcome.reason


def test_retrieve_with_fallback_returns_results_when_healthy():
    outcome = retrieve_with_fallback(_WorksRetriever(), tenant_id="default", query_text="refund policy")
    assert outcome.degraded is False
    assert len(outcome.results) == 1


def test_real_pinecone_client_raises_when_api_key_missing():
    retriever = PineconeRetriever(Settings(pinecone_api_key=""))
    outcome = retrieve_with_fallback(retriever, tenant_id="default", query_text="anything")
    assert outcome.degraded is True
    assert outcome.kind == "pinecone_degraded"
    assert "PINECONE_API_KEY" in outcome.reason


def test_real_pinecone_client_labels_missing_openai_key_as_embedding_failure(monkeypatch):
    """Reproduces the exact bug this guards against: a Pinecone client/index that
    initializes fine but no/invalid OPENAI_API_KEY must be reported as an
    embedding failure, not a Pinecone outage — Pinecone was never even queried.
    """

    class _FakePineconeClient:
        def __init__(self, api_key):
            pass

        def Index(self, name):
            return object()

    monkeypatch.setattr("app.retrieval.pinecone_client.Pinecone", _FakePineconeClient)

    retriever = PineconeRetriever(Settings(pinecone_api_key="fake-pinecone-key-for-test", openai_api_key=""))
    outcome = retrieve_with_fallback(retriever, tenant_id="default", query_text="anything")
    assert outcome.degraded is True
    assert outcome.kind == "embedding_unavailable"
