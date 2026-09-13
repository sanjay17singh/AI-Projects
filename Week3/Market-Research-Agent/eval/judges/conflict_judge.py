"""0-4 conflict-resolution rubric judge. Feeds
eval/evaluators/conflict_resolution.py (aggregate_conflict_resolution).

Rubric (product spec):
  4 = correctly identified, both values preserved, correct provenance,
      preferred value chosen only when justified, correct reason (including
      correctly leaving it unresolved when it should stay unresolved).
  3 = correct but explanation/provenance incomplete.
  2 = identified but safely left unresolved when it *could* have been resolved
      (or resolved when it should not have been, without confidently
      asserting a wrong answer).
  1 = recognized but resolved incorrectly.
  0 = missed entirely, collapsed to one value silently, or confidently wrong.
"""

from pydantic import BaseModel, Field

from app.clients.openai_client import get_chat_model
from app.config import Settings
from app.schemas.analysis import Conflict
from eval.judges.prompts import build_judge_system_prompt, format_evidence_block
from eval.schemas.eval_models import GoldConflict


class ConflictJudgeVerdict(BaseModel):
    score: int = Field(ge=0, le=4)
    reason: str


_TASK = (
    "You are scoring how well an agent handled a single factual conflict (two disagreeing "
    "values for the same field, from possibly-different sources) using this 0-4 rubric:\n\n"
    "4 = the conflict was correctly identified, both values were preserved (not silently "
    "dropped), provenance (which evidence supports which value) is correct, a preferred value "
    "was chosen only when the gold data says one is justified, and the stated reason is "
    "correct. If the gold data says this conflict must remain unresolved or requires human "
    "review, a 4 also requires the agent to have correctly left it unresolved/flagged for "
    "review rather than picking a side — do not penalize a correct 'leave unresolved' as if "
    "it were a failure to decide.\n"
    "3 = correctly identified and correctly resolved (or correctly left unresolved), but the "
    "explanation or provenance is incomplete.\n"
    "2 = the conflict was identified but the agent played it safe by leaving it unresolved "
    "when the gold data indicates it should have been resolvable, or resolved it without a "
    "confidently wrong answer.\n"
    "1 = the conflict was recognized as a conflict but resolved incorrectly (wrong preferred "
    "value or wrong reasoning).\n"
    "0 = the conflict was missed entirely, the two values were silently collapsed into one, "
    "or the agent confidently asserted a wrong resolution.\n\n"
    "Use the gold conflict's must_remain_unresolved/requires_human_review flags to judge "
    "whether the agent's resolution_status was appropriate — an agent that correctly leaves "
    "such a conflict unresolved should score a 4, not be penalized for 'not deciding'."
)


def judge_conflict(
    gold_conflict: GoldConflict,
    agent_conflict: Conflict | None,
    evidence: list[dict],
    settings: Settings,
) -> ConflictJudgeVerdict:
    model = get_chat_model(settings, fast=False, temperature=0.0).with_structured_output(
        ConflictJudgeVerdict
    )

    gold_block = (
        f"field={gold_conflict.field!r}\n"
        f"value_a={gold_conflict.value_a!r} (evidence_ids_a={gold_conflict.evidence_ids_a}, "
        f"source_authority_a={gold_conflict.source_authority_a}, "
        f"published_at_a={gold_conflict.published_at_a})\n"
        f"value_b={gold_conflict.value_b!r} (evidence_ids_b={gold_conflict.evidence_ids_b}, "
        f"source_authority_b={gold_conflict.source_authority_b}, "
        f"published_at_b={gold_conflict.published_at_b})\n"
        f"expected_preferred_value={gold_conflict.expected_preferred_value!r}\n"
        f"expected_resolution_reason={gold_conflict.expected_resolution_reason!r}\n"
        f"must_remain_unresolved={gold_conflict.must_remain_unresolved}\n"
        f"requires_human_review={gold_conflict.requires_human_review}"
    )
    if agent_conflict is None:
        agent_block = "(agent did not report a conflict for this field at all)"
    else:
        values_block = "; ".join(
            f"{v.value!r} (evidence_ids={v.evidence_ids})" for v in agent_conflict.values
        )
        agent_block = (
            f"field={agent_conflict.field!r}\n"
            f"values=[{values_block}]\n"
            f"resolution_status={agent_conflict.resolution_status!r}\n"
            f"preferred_value={agent_conflict.preferred_value!r}\n"
            f"resolution_reason={agent_conflict.resolution_reason!r}"
        )

    messages = [
        ("system", build_judge_system_prompt(_TASK)),
        (
            "human",
            f"Gold (expected) conflict:\n{gold_block}\n\n"
            f"Agent-reported conflict (or absence thereof):\n{agent_block}\n\n"
            f"Frozen evidence:\n{format_evidence_block(evidence)}",
        ),
    ]
    return model.invoke(messages)
