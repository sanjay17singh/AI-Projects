"""LLM + tool logic for competitor discovery. No LangGraph wiring lives here —
graphs/discovery_nodes.py calls these methods from graph nodes."""

from typing import Any

from app.clients.openai_client import get_chat_model
from app.clients.youcom_client import YouComClient
from app.config import Settings
from app.prompts.discovery_prompts import (
    generate_queries_messages,
    normalize_request_messages,
    score_candidates_messages,
)
from app.schemas.discovery import (
    CandidateList,
    CompetitorCandidate,
    NormalizedRequest,
    SearchQueryList,
)


class DiscoveryAgent:
    def __init__(self, settings: Settings, youcom_client: YouComClient):
        self._settings = settings
        self._youcom = youcom_client

    def normalize_request(self, raw_request: dict[str, Any]) -> NormalizedRequest:
        model = get_chat_model(self._settings, fast=True).with_structured_output(NormalizedRequest)
        return model.invoke(normalize_request_messages(raw_request))

    def generate_queries(
        self, normalized_request: dict[str, Any], previous_error: str | None = None
    ) -> list[str]:
        model = get_chat_model(self._settings, fast=True).with_structured_output(SearchQueryList)
        result = model.invoke(generate_queries_messages(normalized_request, previous_error))
        return result.queries

    def search(self, queries: list[str]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for query in queries:
            for hit in self._youcom.search_web(query, category="discovery"):
                results.append(hit.model_dump())
        return results

    def score_candidates(
        self, normalized_request: dict[str, Any], raw_results: list[dict[str, Any]]
    ) -> list[CompetitorCandidate]:
        model = get_chat_model(self._settings, fast=True).with_structured_output(CandidateList)
        result: CandidateList = model.invoke(
            score_candidates_messages(normalized_request, raw_results)
        )
        ranked = sorted(result.candidates, key=lambda c: c.match_score, reverse=True)
        return ranked[:5]
