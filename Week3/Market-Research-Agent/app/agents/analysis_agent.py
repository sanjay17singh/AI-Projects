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
from app.services.analysis_service import assemble_competitor_profile, sanitize_claims

RETRIEVAL_TOP_K = 6


class AnalysisVerificationAgent:
    def __init__(self, settings: Settings, pinecone_client: PineconeClient):
        self._settings = settings
        self._pinecone = pinecone_client
        self._embeddings = get_embeddings_model(settings)

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
            top_k=RETRIEVAL_TOP_K,
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

        return assemble_competitor_profile(str(competitor_id), competitor_name, extracted)

    def _extract(
        self, competitor_name: str, evidence_by_category: dict[str, list[dict]]
    ) -> ExtractedProfile:
        model = get_chat_model(self._settings, fast=False).with_structured_output(ExtractedProfile)
        messages = build_extraction_messages(competitor_name, evidence_by_category)
        try:
            return model.invoke(messages)
        except ValidationError:
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
            try:
                return model.invoke(stricter)
            except ValidationError:
                return ExtractedProfile()
