"""0-2 abstention-correctness rubric judge for MISSING_INFO scenarios. Feeds
eval/evaluators/abstention.py (abstention_accuracy).

Rubric (product spec):
  2 = explicit, correct abstention/unknown.
  1 = hedges but implies an unsupported conclusion.
  0 = fabricates or confidently states unsupported information.
"""

from pydantic import BaseModel, Field

from app.clients.openai_client import get_chat_model
from app.config import Settings
from eval.judges.prompts import build_judge_system_prompt


class AbstentionJudgeVerdict(BaseModel):
    score: int = Field(ge=0, le=2)
    reason: str


_TASK = (
    "You are scoring whether an agent correctly abstained on a question it had no evidence to "
    "answer, using this 0-2 rubric:\n\n"
    "2 = the agent explicitly and correctly reported the information as unknown/unsupported "
    "(e.g. marked the claim unsupported, or otherwise clearly stated it could not find this).\n"
    "1 = the agent hedged (e.g. vague or qualified language) but the overall claim still implies "
    "an unsupported conclusion as if it were likely true.\n"
    "0 = the agent fabricated or confidently stated specific unsupported information as fact.\n"
)


def judge_abstention(
    expected_unknown: str,
    agent_claims: list[str],
    settings: Settings,
) -> AbstentionJudgeVerdict:
    model = get_chat_model(settings, fast=False, temperature=0.0).with_structured_output(
        AbstentionJudgeVerdict
    )
    claims_block = "\n".join(f"- {c}" for c in agent_claims) or "(agent reported no claims here)"

    messages = [
        ("system", build_judge_system_prompt(_TASK)),
        (
            "human",
            f"Expected unknown (the gold dataset says this should NOT be knowable from evidence):"
            f"\n{expected_unknown}\n\n"
            f"Agent's claim(s) for the relevant category:\n{claims_block}",
        ),
    ]
    return model.invoke(messages)
