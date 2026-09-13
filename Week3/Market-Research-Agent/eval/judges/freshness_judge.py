"""0-3 temporal/freshness-correctness rubric judge for TEMPORAL scenarios.
Feeds eval/evaluators/freshness.py (aggregate_freshness).

Rubric (product spec):
  3 = correct current value + explained relationship to any historical value.
  2 = correct current value, no historical context given.
  1 = both current and historical values reported, no determination of which is current.
  0 = stale value presented as current.
"""

from pydantic import BaseModel, Field

from app.clients.openai_client import get_chat_model
from app.config import Settings
from eval.judges.prompts import build_judge_system_prompt, format_evidence_block


class FreshnessJudgeVerdict(BaseModel):
    score: int = Field(ge=0, le=3)
    reason: str


_TASK = (
    "You are scoring whether an agent correctly identified the current (most recent) value for "
    "a field that changed over time, using this 0-3 rubric:\n\n"
    "3 = the agent reported the correct current value AND explained its relationship to the "
    "superseded/historical value (e.g. 'price increased from $X to $Y in <date>').\n"
    "2 = the agent reported the correct current value but gave no historical context.\n"
    "1 = the agent reported both the current and a historical value but did not determine or "
    "state which one is actually current.\n"
    "0 = the agent presented a stale/superseded value as if it were the current one.\n"
)


def judge_freshness(
    expected_current_value: str,
    agent_claims: list[str],
    evidence: list[dict],
    settings: Settings,
) -> FreshnessJudgeVerdict:
    model = get_chat_model(settings, fast=False, temperature=0.0).with_structured_output(
        FreshnessJudgeVerdict
    )
    claims_block = "\n".join(f"- {c}" for c in agent_claims) or "(agent reported no claims here)"

    messages = [
        ("system", build_judge_system_prompt(_TASK)),
        (
            "human",
            f"Expected current value: {expected_current_value}\n\n"
            f"Agent's claim(s) for the relevant category:\n{claims_block}\n\n"
            f"Frozen evidence (check published_at/dates for recency):\n"
            f"{format_evidence_block(evidence)}",
        ),
    ]
    return model.invoke(messages)
