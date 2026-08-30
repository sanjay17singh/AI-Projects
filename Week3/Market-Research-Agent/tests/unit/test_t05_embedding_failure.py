"""T05 (-): Pinecone upsert failure marks research_evidence.embedding_status
='failed' + logs a warning, doesn't crash the run."""

import uuid

from app.agents.web_research_agent import WebResearchAgent
from app.db.models import ResearchEvidence
from app.schemas.research import RawSearchResult
from tests.fixtures.fake_pinecone import FakePineconeClient


class FakeEmbeddings:
    def embed_documents(self, texts):
        return [[0.0, 0.0, 0.0] for _ in texts]


class FakeYouCom:
    def search_web(self, query, category, count=10):
        if category != "pricing":
            return []
        return [
            RawSearchResult(
                title="Acme pricing",
                url="https://acme.com/pricing",
                snippet="Plans start at $29/mo.",
                highlights=None,
                published_at=None,
                category="pricing",
                query_used=query,
                source_type="web",
            )
        ]

    def search_news(self, query, news_window_days, count=10):
        return []


def test_pinecone_upsert_failure_marks_embedding_status_failed_and_does_not_raise(
    db_session, settings, monkeypatch
):
    monkeypatch.setattr(
        "app.agents.web_research_agent.get_embeddings_model", lambda settings: FakeEmbeddings()
    )
    pinecone = FakePineconeClient()
    pinecone.upsert_should_fail = True

    agent = WebResearchAgent(settings, [FakeYouCom()], pinecone)
    run_id = uuid.uuid4()
    competitor_id = uuid.uuid4()

    result = agent.research(
        db=db_session,
        run_id=run_id,
        workspace_id="default",
        competitor_id=competitor_id,
        competitor_name="Acme",
        news_window_days=60,
        categories=["pricing"],
    )

    assert result.failed is False  # the run itself doesn't crash/fail
    assert any("embedding_storage_failed" in w for w in result.warnings)
    assert result.evidence_ids == []  # not usable for retrieval since it was never embedded

    row = (
        db_session.query(ResearchEvidence)
        .filter_by(run_id=run_id, competitor_id=competitor_id)
        .one()
    )
    assert row.embedding_status == "failed"
    assert row.chunk_count == 0
