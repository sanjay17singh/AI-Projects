"""Structured-output and shared data models for the billing support bot."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Category = Literal[
    "refund",
    "proration",
    "payment_failure",
    "cancellation",
    "upgrade_downgrade",
    "invoice_dispute",
    "general_policy",
]

SourceType = Literal["ticket", "faq", "pricing_doc"]

CATEGORY_LABELS: dict[str, str] = {
    "refund": "Refund",
    "proration": "Proration",
    "payment_failure": "Payment Failure",
    "cancellation": "Cancellation",
    "upgrade_downgrade": "Upgrade/Downgrade",
    "invoice_dispute": "Invoice Dispute",
    "general_policy": "General Policy",
}

SOURCE_TYPE_LABELS: dict[str, str] = {
    "ticket": "Support Ticket",
    "faq": "FAQ",
    "pricing_doc": "Pricing Doc",
}


class ClassificationResult(BaseModel):
    """Output of the classify node: intent category + any dollar amount in the query."""

    category: Category = Field(description="Best-matching billing support category for the query.")
    dollar_amount: Optional[float] = Field(
        default=None,
        description="Dollar amount explicitly mentioned in the customer's query, if any. Null if none.",
    )


class BotResponse(BaseModel):
    """Structured output of the generation node (OpenAI JSON-mode / structured output)."""

    answer: Optional[str] = Field(
        default=None,
        description="Plain-language answer grounded ONLY in the retrieved sources. Null if not confidently answerable.",
    )
    citations: list[str] = Field(
        default_factory=list,
        description="source_id values (from retrieved sources) that support the answer.",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Model's confidence (0-1) that the answer is fully correct and grounded in the retrieved sources.",
    )
    category: Category = Field(description="Billing support category for this query.")
    dollar_amount: Optional[float] = Field(
        default=None,
        description="Dollar amount explicitly involved in the query, if any. Null/0 if none.",
    )
    escalate: bool = Field(description="True if the model itself believes this should go to a human agent.")
    escalation_reason: Optional[str] = Field(
        default=None,
        description="Short reason for escalation, if escalate is True. Null otherwise.",
    )


class RetrievedDoc(BaseModel):
    """A single retrieved chunk, annotated for citation display.

    dense_rank / bm25_rank / rrf_score expose the hybrid fusion mechanics (which
    retriever(s) surfaced this chunk, at what rank, and its resulting Reciprocal
    Rank Fusion score) so the UI can show retrieval transparency, not just the
    final fused order.
    """

    source_id: str
    source_type: SourceType
    category: str
    text: str
    chunk_id: Optional[str] = None
    dense_rank: Optional[int] = None
    bm25_rank: Optional[int] = None
    rrf_score: Optional[float] = None

    @property
    def label(self) -> str:
        return f"{SOURCE_TYPE_LABELS.get(self.source_type, self.source_type)}: {self.source_id}"


class PriorEscalation(BaseModel):
    category: str
    reason: Optional[str] = None


class CustomerMemory(BaseModel):
    """Per-customer long-term context pulled from Mem0. Context only — never a citation source."""

    plan_tier: Optional[str] = None
    prior_issues: list[str] = Field(default_factory=list)
    prior_escalations: list[PriorEscalation] = Field(default_factory=list)
    preferences: list[str] = Field(default_factory=list)

    def escalation_count_for(self, category: str) -> int:
        return sum(1 for e in self.prior_escalations if e.category == category)

    def as_context_text(self) -> str:
        if not any([self.plan_tier, self.prior_issues, self.prior_escalations, self.preferences]):
            return "No prior context available for this customer."
        parts = []
        if self.plan_tier:
            parts.append(f"Plan tier: {self.plan_tier}.")
        if self.prior_issues:
            parts.append("Prior issues raised: " + "; ".join(self.prior_issues) + ".")
        if self.prior_escalations:
            esc = ", ".join(f"{e.category}" + (f" ({e.reason})" if e.reason else "") for e in self.prior_escalations)
            parts.append(f"Prior escalations: {esc}.")
        if self.preferences:
            parts.append("Stated preferences: " + "; ".join(self.preferences) + ".")
        return " ".join(parts)


class MemorySummary(BaseModel):
    """Durable, session-end summary extracted for Mem0. Never the full transcript."""

    is_durable: bool = Field(description="True if anything below is worth remembering long-term for this customer.")
    issue_summary: Optional[str] = Field(
        default=None, description="One short sentence summarizing the issue and how it was left, if durable."
    )
    plan_tier: Optional[str] = Field(
        default=None, description="Plan tier mentioned by the customer (Starter/Pro/Business/Enterprise), if any."
    )
    preference: Optional[str] = Field(
        default=None, description="A stated durable preference (e.g. 'wants email confirmation of refunds'), if any."
    )


MONEY_MOVING_CATEGORIES: set[str] = {"refund", "proration", "invoice_dispute"}
MONEY_MOVING_CONFIDENCE_THRESHOLD = 0.90
MONEY_MOVING_DOLLAR_CAP = 100.0
MODERATE_CONFIDENCE_THRESHOLD = 0.60
MEMORY_ESCALATION_OVERRIDE_COUNT = 2
