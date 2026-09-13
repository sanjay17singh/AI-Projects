"""0-4 evidence-faithfulness rubric judge. Feeds
eval/evaluators/faithfulness.py (aggregate_faithfulness) and
eval/evaluators/unsupported_claims.py (via unsupported_items).

Rubric (product spec):
  4 = every material claim is fully supported by its cited evidence.
  3 = mostly supported, minor overstatement.
  2 = partially supported.
  1 = weak relationship between claim and cited evidence.
  0 = unsupported or hallucinated.
"""

from pydantic import BaseModel, Field

from app.clients.openai_client import get_chat_model
from app.config import Settings
from app.schemas.analysis import CompetitorProfile
from app.schemas.common import ALL_PROFILE_CATEGORIES
from eval.judges.prompts import build_judge_system_prompt, format_evidence_block


class FaithfulnessJudgeVerdict(BaseModel):
    score: int = Field(ge=0, le=4)
    unsupported_items: list[str] = Field(
        default_factory=list,
        description="Claim values judged unsupported by their cited evidence.",
    )
    reason: str


_TASK = (
    "You are scoring how faithful a competitor profile's claims are to the evidence text cited "
    "for them, using this 0-4 rubric:\n\n"
    "4 = every material claim is fully supported by the evidence cited for it.\n"
    "3 = mostly supported, with only a minor overstatement beyond what the evidence says.\n"
    "2 = partially supported — the claim goes noticeably beyond its cited evidence.\n"
    "1 = only a weak relationship between the claim and its cited evidence.\n"
    "0 = the claim is unsupported by, or contradicts, its cited evidence (hallucinated).\n\n"
    "Judge only claims that are not marked is_unsupported (those are deliberately empty/"
    "abstained claims and are never counted against faithfulness). List every claim value you "
    "judge as unsupported (score of 0 or 1 for that specific claim) in unsupported_items."
)


def judge_faithfulness(
    profile: CompetitorProfile,
    evidence: list[dict],
    settings: Settings,
    categories: list[str] | None = None,
) -> FaithfulnessJudgeVerdict:
    model = get_chat_model(settings, fast=False, temperature=0.0).with_structured_output(
        FaithfulnessJudgeVerdict
    )

    categories = categories or ALL_PROFILE_CATEGORIES
    claim_lines = []
    for category in categories:
        for claim in getattr(profile, category, []):
            if claim.is_unsupported:
                continue
            claim_lines.append(
                f"- [{category}] {claim.value!r} (cited evidence_ids={claim.evidence_ids})"
            )
    claims_block = "\n".join(claim_lines) or "(no material claims to check)"

    messages = [
        ("system", build_judge_system_prompt(_TASK)),
        (
            "human",
            f"Competitor: {profile.competitor_name}\n\n"
            f"Claims to check:\n{claims_block}\n\n"
            f"Frozen evidence (only the cited evidence_ids are relevant):\n"
            f"{format_evidence_block(evidence)}",
        ),
    ]
    return model.invoke(messages)
