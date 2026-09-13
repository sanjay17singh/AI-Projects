"""Shared prompt-building helpers for every LLM-as-judge in eval/judges/.

Every judge in this package must prepend/append `NO_OUTSIDE_KNOWLEDGE_GUARD`
to its system prompt — it is the one rule that keeps a judge from silently
falling back on the model's own world knowledge of a (frequently fictional,
for the Golden Dataset) company, or inventing an item (a red flag, a claim)
that is absent from both the agent output and the reference materials it was
handed.
"""

NO_OUTSIDE_KNOWLEDGE_GUARD = (
    "You must reason ONLY from the materials explicitly provided to you in this "
    "prompt: the scenario input, the reference_outputs (gold expectations), and "
    "the frozen evidence text supplied below. Never use general world knowledge "
    "about any company named here, real or fictional. Never invent, assume, or "
    "credit an item (a claim, a red flag, a conflict, a fact) that does not "
    "literally appear in the agent output or the reference materials you were "
    "given. If the provided materials are insufficient to judge something, say "
    "so in your reason rather than guessing."
)


def build_judge_system_prompt(task_description: str) -> str:
    """Wraps a judge-specific task description with the shared guard, front
    and back, so it can't be missed by the model regardless of prompt length."""
    return (
        f"{NO_OUTSIDE_KNOWLEDGE_GUARD}\n\n"
        f"{task_description}\n\n"
        f"Reminder: {NO_OUTSIDE_KNOWLEDGE_GUARD}"
    )


def format_evidence_block(evidence: list[dict]) -> str:
    """Renders a list of {"evidence_id", "text"} (or EvidenceRecord-shaped)
    dicts as a single text block for a judge prompt."""
    if not evidence:
        return "(no evidence provided)"
    parts = []
    for item in evidence:
        eid = item.get("evidence_id", "unknown")
        text = item.get("content") or item.get("text") or ""
        parts.append(f"[{eid}]\n{text}")
    return "\n\n".join(parts)
