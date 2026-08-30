"""T01 (+): 5 raw search results score/classify into distinct
direct/indirect/emerging candidates with valid 0-1 scores."""

from app.agents.discovery_agent import DiscoveryAgent
from app.schemas.discovery import CandidateList, Classification, CompetitorCandidate
from tests.fixtures.fake_llm import FakeChatModel


class FakeYouCom:
    def search_web(self, query, category, count=10):
        return []


def test_score_candidates_returns_five_with_valid_scores_and_classifications(settings, monkeypatch):
    candidates = CandidateList(
        candidates=[
            CompetitorCandidate(
                company_name=f"Competitor {i}",
                website=f"https://competitor{i}.com",
                match_score=round(0.9 - 0.1 * i, 2),
                classification=[
                    Classification.DIRECT,
                    Classification.DIRECT,
                    Classification.INDIRECT,
                    Classification.INDIRECT,
                    Classification.EMERGING,
                ][i],
                explanation=f"Explanation {i}",
                source_urls=[f"https://competitor{i}.com"],
            )
            for i in range(5)
        ]
    )
    fake_model = FakeChatModel({CandidateList: candidates})
    monkeypatch.setattr(
        "app.agents.discovery_agent.get_chat_model", lambda settings, fast=False: fake_model
    )

    agent = DiscoveryAgent(settings, FakeYouCom())
    result = agent.score_candidates({"target_company_name": "Acme"}, [])

    assert len(result) == 5
    for candidate in result:
        assert 0.0 <= candidate.match_score <= 1.0
    classifications = {c.classification for c in result}
    assert classifications == {
        Classification.DIRECT,
        Classification.INDIRECT,
        Classification.EMERGING,
    }
    # sorted descending by score
    assert [c.match_score for c in result] == sorted([c.match_score for c in result], reverse=True)
