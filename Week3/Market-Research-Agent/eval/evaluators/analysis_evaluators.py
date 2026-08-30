"""Evaluators for the Analysis and Verification Agent. `example.inputs`
carries the fixture evidence used for that row (see run_analysis_eval.py);
`run.outputs` is the CompetitorProfile (as a dict) the agent produced."""

from pydantic import BaseModel, Field

from app.clients.openai_client import get_chat_model
from app.config import get_settings
from app.schemas.common import ALL_PROFILE_CATEGORIES


def _all_claims(profile: dict):
    for category in ALL_PROFILE_CATEGORIES:
        for claim in profile.get(category, []):
            yield category, claim


def groundedness(run, example) -> dict:
    """Programmatic, not LLM-judged: every claim's evidence_ids must resolve
    to evidence that was actually part of the fixture retrieved for this row
    — catches a hallucinated citation directly."""
    profile = run.outputs
    valid_ids = {e["evidence_id"] for e in example.inputs["evidence"]}

    ungrounded = []
    for category, claim in _all_claims(profile):
        if claim.get("is_unsupported"):
            continue
        for eid in claim.get("evidence_ids", []):
            if eid not in valid_ids:
                ungrounded.append((category, eid))

    return {
        "key": "groundedness",
        "score": 1.0 if not ungrounded else 0.0,
        "comment": f"ungrounded citations: {ungrounded}" if ungrounded else "all citations resolve",
    }


def coverage_sanity(run, example) -> dict:
    """The reported evidence_coverage_score must match the deterministic
    formula — if it doesn't, either the agent or the formula drifted."""
    from app.schemas.analysis import ClaimField, ExtractedProfile
    from app.services.analysis_service import compute_coverage_score

    profile = run.outputs
    extracted = ExtractedProfile(
        **{
            category: [ClaimField(**claim) for claim in profile.get(category, [])]
            for category in ALL_PROFILE_CATEGORIES
        }
    )
    recomputed = compute_coverage_score(extracted)
    reported = profile.get("evidence_coverage_score")
    return {
        "key": "coverage_sanity",
        "score": 1.0 if abs(recomputed - reported) < 1e-6 else 0.0,
        "comment": f"reported={reported} recomputed={recomputed}",
    }


class FaithfulnessJudgment(BaseModel):
    faithful: bool = Field(description="Does the claim say only what the cited evidence supports?")
    reasoning: str


def faithfulness_llm_judge(run, example) -> dict:
    """LLM-as-judge: for each grounded claim, does the claim text over-claim
    beyond what its cited evidence actually says?"""
    settings = get_settings()
    model = get_chat_model(settings, fast=False).with_structured_output(FaithfulnessJudgment)
    evidence_by_id = {e["evidence_id"]: e["text"] for e in example.inputs["evidence"]}

    profile = run.outputs
    unfaithful = []
    checked = 0
    for category, claim in _all_claims(profile):
        if claim.get("is_unsupported") or not claim.get("evidence_ids"):
            continue
        cited_text = "\n".join(
            evidence_by_id.get(eid, "") for eid in claim["evidence_ids"] if eid in evidence_by_id
        )
        if not cited_text:
            continue
        checked += 1
        judgment: FaithfulnessJudgment = model.invoke(
            [
                (
                    "system",
                    "Judge whether a claim is faithful to its cited evidence — it must not state "
                    "more than the evidence actually supports.",
                ),
                ("human", f"Claim: {claim['value']}\n\nCited evidence:\n{cited_text}"),
            ]
        )
        if not judgment.faithful:
            unfaithful.append((category, claim["value"], judgment.reasoning))

    score = 1.0 if not unfaithful else max(0.0, 1.0 - len(unfaithful) / max(checked, 1))
    return {"key": "faithfulness", "score": score, "comment": f"unfaithful claims: {unfaithful}"}


ANALYSIS_EVALUATORS = [groundedness, coverage_sanity, faithfulness_llm_judge]
