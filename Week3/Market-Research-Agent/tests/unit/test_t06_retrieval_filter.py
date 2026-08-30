"""T06 (+): category-filtered retrieval only returns vectors matching
run_id/competitor_id/category."""

from app.agents.analysis_agent import AnalysisVerificationAgent
from tests.fixtures.fake_pinecone import FakePineconeClient


class FakeEmbeddings:
    def embed_query(self, text):
        return [0.0, 0.0, 0.0]


def test_retrieval_only_returns_matching_run_competitor_category(settings, monkeypatch):
    monkeypatch.setattr(
        "app.agents.analysis_agent.get_embeddings_model", lambda settings: FakeEmbeddings()
    )
    pinecone = FakePineconeClient()
    namespace = "default"
    # Matching vector (should be returned)
    pinecone.upsert(
        [
            (
                "v1",
                [0.0, 0.0, 0.0],
                {
                    "run_id": "run-1",
                    "competitor_id": "comp-1",
                    "category": "pricing",
                    "evidence_id": "e1",
                    "canonical_url": "https://a.com",
                    "text": "matching text",
                },
            )
        ],
        namespace=namespace,
    )
    # Wrong competitor
    pinecone.upsert(
        [
            (
                "v2",
                [0.0, 0.0, 0.0],
                {
                    "run_id": "run-1",
                    "competitor_id": "comp-OTHER",
                    "category": "pricing",
                    "evidence_id": "e2",
                    "canonical_url": "https://b.com",
                    "text": "wrong competitor",
                },
            )
        ],
        namespace=namespace,
    )
    # Wrong category
    pinecone.upsert(
        [
            (
                "v3",
                [0.0, 0.0, 0.0],
                {
                    "run_id": "run-1",
                    "competitor_id": "comp-1",
                    "category": "news",
                    "evidence_id": "e3",
                    "canonical_url": "https://c.com",
                    "text": "wrong category",
                },
            )
        ],
        namespace=namespace,
    )
    # Wrong run
    pinecone.upsert(
        [
            (
                "v4",
                [0.0, 0.0, 0.0],
                {
                    "run_id": "run-OTHER",
                    "competitor_id": "comp-1",
                    "category": "pricing",
                    "evidence_id": "e4",
                    "canonical_url": "https://d.com",
                    "text": "wrong run",
                },
            )
        ],
        namespace=namespace,
    )

    agent = AnalysisVerificationAgent(settings, pinecone)
    items = agent._retrieve_category(
        workspace_id="default",
        run_id="run-1",
        competitor_id="comp-1",
        competitor_name="Acme",
        category="pricing",
    )

    assert len(items) == 1
    assert items[0]["evidence_id"] == "e1"
