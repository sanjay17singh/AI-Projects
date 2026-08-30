"""Evaluators for the Discovery Agent. Each takes (run, example) — LangSmith's
standard evaluator signature — and returns a {"key", "score", "comment"} dict.
`run.outputs` is whatever run_discovery_eval.py's target function returned;
`example.inputs` is one row from datasets/discovery_examples.json."""

from pydantic import BaseModel, Field

from app.clients.openai_client import get_chat_model
from app.config import get_settings


class RelevanceJudgment(BaseModel):
    relevance_score: float = Field(ge=0.0, le=1.0, description="0=irrelevant, 1=highly relevant")
    reasoning: str


def exactly_five_candidates(run, example) -> dict:
    candidates = run.outputs.get("candidates", [])
    return {
        "key": "exactly_five_candidates",
        "score": 1.0 if len(candidates) == 5 else 0.0,
        "comment": f"got {len(candidates)} candidates",
    }


def scores_in_valid_range(run, example) -> dict:
    candidates = run.outputs.get("candidates", [])
    valid = all(0.0 <= c.get("match_score", -1) <= 1.0 for c in candidates)
    return {"key": "scores_in_valid_range", "score": 1.0 if valid else 0.0}


def classification_diversity(run, example) -> dict:
    candidates = run.outputs.get("candidates", [])
    classifications = {c.get("classification") for c in candidates}
    return {
        "key": "classification_diversity",
        "score": 1.0 if len(classifications) >= 2 else 0.0,
        "comment": f"classifications seen: {sorted(classifications)}",
    }


def relevance_llm_judge(run, example) -> dict:
    """LLM-as-judge: are the returned competitors actually relevant to the
    target company's industry/geography/segment?"""
    settings = get_settings()
    model = get_chat_model(settings, fast=False).with_structured_output(RelevanceJudgment)

    request = example.inputs
    candidates = run.outputs.get("candidates", [])
    candidates_block = "\n".join(
        f"- {c.get('company_name')}: {c.get('explanation')}" for c in candidates
    )
    messages = [
        (
            "system",
            "You judge whether a list of proposed competitors is actually relevant to a "
            "target company. Score 0-1 overall relevance across the whole list.",
        ),
        (
            "human",
            f"Target company: {request.get('target_company_name')}\n"
            f"Industry: {request.get('industry')}\n"
            f"Geography: {request.get('geography')}\n"
            f"Customer segment: {request.get('customer_segment')}\n\n"
            f"Proposed competitors:\n{candidates_block}",
        ),
    ]
    judgment: RelevanceJudgment = model.invoke(messages)
    return {"key": "relevance", "score": judgment.relevance_score, "comment": judgment.reasoning}


DISCOVERY_EVALUATORS = [
    exactly_five_candidates,
    scores_in_valid_range,
    classification_diversity,
    relevance_llm_judge,
]
