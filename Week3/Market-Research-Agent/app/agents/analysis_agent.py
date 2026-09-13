"""Retrieval + structured extraction for one competitor. One instance per
competitor. Verification is folded into this agent for the MVP (no separate
5th agent) — the ClaimField validators + sanitize_claims() are the
'verification' step."""

from uuid import UUID

from pydantic import ValidationError

from app.clients.openai_client import get_chat_model, get_embeddings_model
from app.clients.pinecone_client import PineconeClient
from app.config import Settings
from app.prompts.analysis_prompts import build_extraction_messages, build_retrieval_query
from app.schemas.analysis import ClaimField, CompetitorProfile, ExtractedProfile
from app.schemas.common import ALL_PROFILE_CATEGORIES
from app.schemas.research import storage_category_for
from app.services.analysis_service import (
    assemble_competitor_profile,
    sanitize_claims,
    sanitize_red_flags,
)

# Fallback used only if Settings somehow lacks the field (e.g. an older
# fixture/monkeypatch in a test) — kept in sync with Settings.retrieval_top_k.
RETRIEVAL_TOP_K = 6


class AnalysisVerificationAgent:
    def __init__(self, settings: Settings, pinecone_client: PineconeClient):
        self._settings = settings
        self._pinecone = pinecone_client
        self._embeddings = get_embeddings_model(settings)
        # Real token usage from the most recent _extract() call, keyed by
        # "tokens_in"/"tokens_out". Populated on a best-effort basis (empty
        # dict if the model response carried no usage_metadata, e.g. a fake
        # in tests) — callers should fall back to estimates when empty.
        self.last_usage: dict[str, int] = {}

    def _retrieve_category(
        self,
        workspace_id: str,
        run_id: UUID,
        competitor_id: UUID,
        competitor_name: str,
        category: str,
    ) -> list[dict]:
        query_text = build_retrieval_query(competitor_name=competitor_name, category=category)
        vector = self._embeddings.embed_query(query_text)
        matches = self._pinecone.query(
            vector=vector,
            namespace=str(workspace_id),
            top_k=getattr(self._settings, "retrieval_top_k", RETRIEVAL_TOP_K),
            filter={
                "run_id": {"$eq": str(run_id)},
                "competitor_id": {"$eq": str(competitor_id)},
                "category": {"$eq": storage_category_for(category)},
            },
        )
        return [
            {
                "evidence_id": m["metadata"]["evidence_id"],
                "url": m["metadata"]["canonical_url"],
                "text": m["metadata"]["text"],
            }
            for m in matches
        ]

    def analyze(
        self,
        workspace_id: str,
        run_id: UUID,
        competitor_id: UUID,
        competitor_name: str,
        categories: list[str] | None = None,
    ) -> CompetitorProfile:
        categories = categories or ALL_PROFILE_CATEGORIES
        evidence_by_category: dict[str, list[dict]] = {}
        valid_evidence_ids: set[str] = set()
        for category in categories:
            items = self._retrieve_category(
                workspace_id, run_id, competitor_id, competitor_name, category
            )
            evidence_by_category[category] = items
            valid_evidence_ids.update(item["evidence_id"] for item in items)

        extracted = self._extract(competitor_name, evidence_by_category)

        for category in categories:
            claims: list[ClaimField] = getattr(extracted, category)
            setattr(extracted, category, sanitize_claims(claims, valid_evidence_ids))
        extracted.red_flags = sanitize_red_flags(extracted.red_flags, valid_evidence_ids)

        return assemble_competitor_profile(str(competitor_id), competitor_name, extracted)

    def _extract(
        self, competitor_name: str, evidence_by_category: dict[str, list[dict]]
    ) -> ExtractedProfile:
        # include_raw=True gives us the raw AIMessage alongside the parsed
        # model, which is the only way to read real token usage
        # (usage_metadata) for accurate cost tracking (see
        # services/cost_service.record_cost callers in graphs/analysis_nodes.py).
        # It also means a parsing failure comes back as parsed=None instead
        # of a raised ValidationError, which is what the retry-then-fallback
        # logic below checks for.
        model = get_chat_model(self._settings, fast=False).with_structured_output(
            ExtractedProfile, include_raw=True
        )
        messages = build_extraction_messages(competitor_name, evidence_by_category)

        profile = self._invoke_and_record_usage(model, messages)
        if profile is not None:
            return profile

        # One stricter retry, per the product requirement, before falling
        # back to an all-unsupported profile.
        stricter = messages + [
            (
                "human",
                "Your previous answer had a claim value without evidence_ids. Every "
                "non-unsupported value must include at least one evidence_id from the "
                "evidence shown above. Try again, following that rule exactly.",
            )
        ]
        profile = self._invoke_and_record_usage(model, stricter)
        if profile is not None:
            return profile
        return ExtractedProfile()

    def _invoke_and_record_usage(self, model, messages) -> ExtractedProfile | None:
        try:
            result = model.invoke(messages)
        except ValidationError:
            return None

        raw = result.get("raw") if isinstance(result, dict) else None
        usage = getattr(raw, "usage_metadata", None) if raw is not None else None
        if usage:
            self.last_usage = {
                "tokens_in": usage.get("input_tokens", 0) or 0,
                "tokens_out": usage.get("output_tokens", 0) or 0,
            }
        return result.get("parsed") if isinstance(result, dict) else result
