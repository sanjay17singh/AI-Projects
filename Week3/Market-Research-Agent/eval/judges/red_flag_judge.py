"""Semantic matching between the agent's RedFlags and the Golden Dataset's
GoldRedFlags — wording differs between the two so exact-ID matching doesn't
work. Feeds eval/evaluators/red_flag_recall.py and red_flag_precision.py."""

from pydantic import BaseModel, Field

from app.clients.openai_client import get_chat_model
from app.config import Settings
from app.schemas.analysis import RedFlag
from eval.judges.prompts import build_judge_system_prompt, format_evidence_block
from eval.schemas.eval_models import GoldRedFlag


class RedFlagMatchResult(BaseModel):
    matched_gold_ids: list[str] = Field(
        default_factory=list,
        description="red_flag_id of every GoldRedFlag correctly identified by some agent RedFlag.",
    )
    correct_agent_flag_ids: list[str] = Field(
        default_factory=list,
        description="red_flag_id of every agent RedFlag judged to correctly correspond to a gold "
        "flag.",
    )
    reason: str


_TASK = (
    "You are comparing a list of red flags an agent reported about a competitor against a "
    "list of gold (expected) red flags for the same competitor, using the frozen evidence "
    "text as context.\n\n"
    "Two flags match when they describe the same underlying negative development, even if "
    "worded very differently (e.g. 'price hike of 20%' and 'raised subscription cost by a "
    "fifth' describe the same event). A gold flag with no corresponding agent flag is unmatched. "
    "An agent flag that does not correspond to any gold flag is not 'correct' for this task — "
    "it may still be true, but only mark an agent flag as correct if it matches a specific gold "
    "flag or is clearly and directly supported as a genuine red flag by the evidence provided.\n\n"
    "Never invent a red flag that appears in neither list. Return the gold red_flag_ids that were "
    "correctly identified (matched_gold_ids) and the agent red_flag_ids that were judged correct "
    "(correct_agent_flag_ids)."
)


def judge_red_flags(
    agent_red_flags: list[RedFlag],
    gold_red_flags: list[GoldRedFlag],
    evidence: list[dict],
    settings: Settings,
) -> RedFlagMatchResult:
    model = get_chat_model(settings, fast=False, temperature=0.0).with_structured_output(
        RedFlagMatchResult
    )

    agent_block = "\n".join(
        f"- id={f.red_flag_id!r} type={f.type!r} severity={f.severity!r}: {f.description}"
        for f in agent_red_flags
    ) or "(agent reported no red flags)"
    gold_block = "\n".join(
        f"- id={f.red_flag_id!r} type={f.type!r} severity={f.severity!r} "
        f"critical={f.is_critical}: {f.description}"
        for f in gold_red_flags
    ) or "(no gold red flags expected)"

    messages = [
        ("system", build_judge_system_prompt(_TASK)),
        (
            "human",
            f"Agent-reported red flags:\n{agent_block}\n\n"
            f"Gold (expected) red flags:\n{gold_block}\n\n"
            f"Frozen evidence:\n{format_evidence_block(evidence)}",
        ),
    ]
    return model.invoke(messages)
