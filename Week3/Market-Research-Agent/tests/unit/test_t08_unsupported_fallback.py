"""T08 (+): zero evidence for a field falls back to "Not publicly
available"."""

from app.agents.analysis_agent import AnalysisVerificationAgent
from app.schemas.analysis import ExtractedProfile
from app.schemas.common import UNSUPPORTED_VALUE
from tests.fixtures.fake_llm import FakeChatModel
from tests.fixtures.fake_pinecone import FakePineconeClient


class FakeEmbeddings:
    def embed_query(self, text):
        return [0.0, 0.0, 0.0]


def test_no_evidence_falls_back_to_unsupported(settings, monkeypatch):
    monkeypatch.setattr(
        "app.agents.analysis_agent.get_embeddings_model", lambda settings: FakeEmbeddings()
    )
    monkeypatch.setattr(
        "app.agents.analysis_agent.get_chat_model",
        lambda settings, fast=False: FakeChatModel({ExtractedProfile: ExtractedProfile()}),
    )

    agent = AnalysisVerificationAgent(
        settings, FakePineconeClient()
    )  # empty store -> no matches anywhere
    profile = agent.analyze(
        workspace_id="default",
        run_id="run-1",
        competitor_id="comp-1",
        competitor_name="Acme",
        categories=["pricing"],
    )

    assert profile.pricing[0].value == UNSUPPORTED_VALUE
    assert profile.pricing[0].is_unsupported is True
    assert profile.pricing[0].evidence_ids == []
