"""Supplementary coverage: WebResearchAgent merges results from every
configured search client (not just the first one), and dedup still works
correctly across providers when they happen to return the same URL."""

import uuid

from app.agents.web_research_agent import WebResearchAgent
from app.db.models import ResearchEvidence
from app.schemas.research import RawSearchResult


class FakeEmbeddings:
    def embed_documents(self, texts):
        return [[0.0, 0.0, 0.0] for _ in texts]


class FakeProviderA:
    PROVIDER_NAME = "you_com"

    def search_web(self, query, category, count=10):
        return [
            RawSearchResult(
                title="From A",
                url="https://a.example.com/pricing",
                snippet="Pricing per provider A.",
                category=category,
                query_used=query,
                source_type="web",
                provider="you_com",
            )
        ]

    def search_news(self, query, news_window_days, count=10):
        return []


class FakeProviderB:
    PROVIDER_NAME = "serper"

    def search_web(self, query, category, count=10):
        return [
            RawSearchResult(
                title="From B",
                url="https://b.example.com/pricing",
                snippet="Pricing per provider B.",
                category=category,
                query_used=query,
                source_type="web",
                provider="serper",
            )
        ]

    def search_news(self, query, news_window_days, count=10):
        return []


class FakePinecone:
    def upsert(self, vectors, namespace):
        pass


def test_results_from_both_providers_are_ingested(db_session, settings, monkeypatch):
    monkeypatch.setattr(
        "app.agents.web_research_agent.get_embeddings_model", lambda settings: FakeEmbeddings()
    )
    agent = WebResearchAgent(settings, [FakeProviderA(), FakeProviderB()], FakePinecone())
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

    assert len(result.evidence_ids) == 2  # one evidence row per provider's distinct URL
    rows = db_session.query(ResearchEvidence).filter_by(run_id=run_id).all()
    assert {row.provider for row in rows} == {"you_com", "serper"}


def test_provider_names_reflects_configured_clients(settings):
    agent = WebResearchAgent(settings, [FakeProviderA(), FakeProviderB()], FakePinecone())
    assert agent.provider_names == ["you_com", "serper"]

    agent_single = WebResearchAgent(settings, [FakeProviderA()], FakePinecone())
    assert agent_single.provider_names == ["you_com"]
