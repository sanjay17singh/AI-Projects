"""Per-category escalation thresholds and the escalation decision rule.

Escalation is intentionally centralized here (not left to the LLM) so the
decision is deterministic and auditable, per the project's core design
principle: the bot refuses to guess.
"""

from __future__ import annotations

from typing import Optional

from schemas import (
    MEMORY_ESCALATION_OVERRIDE_COUNT,
    MODERATE_CONFIDENCE_THRESHOLD,
    MONEY_MOVING_CATEGORIES,
    MONEY_MOVING_CONFIDENCE_THRESHOLD,
    MONEY_MOVING_DOLLAR_CAP,
    BotResponse,
    CustomerMemory,
)

THRESHOLDS: dict[str, float] = {
    "refund": MONEY_MOVING_CONFIDENCE_THRESHOLD,
    "proration": MONEY_MOVING_CONFIDENCE_THRESHOLD,
    "invoice_dispute": MONEY_MOVING_CONFIDENCE_THRESHOLD,
    "general_policy": MODERATE_CONFIDENCE_THRESHOLD,
    "payment_failure": MODERATE_CONFIDENCE_THRESHOLD,
    "cancellation": MODERATE_CONFIDENCE_THRESHOLD,
    "upgrade_downgrade": MODERATE_CONFIDENCE_THRESHOLD,
}


def decide(response: BotResponse, memory: Optional[CustomerMemory]) -> tuple[bool, Optional[str]]:
    """Return (escalate, escalation_reason), final and authoritative over the LLM's own guess."""

    category = response.category
    threshold = THRESHOLDS.get(category, MODERATE_CONFIDENCE_THRESHOLD)
    dollar_amount = response.dollar_amount or 0.0

    if response.escalate:
        return True, response.escalation_reason or "Model flagged this query for escalation."

    if category in MONEY_MOVING_CATEGORIES and dollar_amount > MONEY_MOVING_DOLLAR_CAP:
        return True, (
            f"Dollar amount (${dollar_amount:,.2f}) exceeds the ${MONEY_MOVING_DOLLAR_CAP:,.2f} "
            f"auto-escalation cap for {category}."
        )

    if response.confidence < threshold:
        return True, (
            f"Confidence {response.confidence:.2f} is below the {threshold:.2f} threshold for {category}."
        )

    if memory is not None:
        prior_count = memory.escalation_count_for(category)
        if prior_count >= MEMORY_ESCALATION_OVERRIDE_COUNT:
            return True, (
                f"Customer has {prior_count} prior escalations in {category}; "
                "escalating immediately per memory policy rather than re-attempting a bot answer."
            )

    return False, None
