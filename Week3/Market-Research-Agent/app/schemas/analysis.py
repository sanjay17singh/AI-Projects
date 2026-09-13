from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import COVERAGE_CATEGORIES, UNSUPPORTED_VALUE, Confidence

Severity = Literal["low", "medium", "high", "critical"]
ResolutionStatus = Literal["resolved", "unresolved", "human_review_required"]


class ClaimField(BaseModel):
    """One extracted fact or inference. Every non-unsupported value must carry
    at least one evidence_id — this is what makes 'require evidence for every
    factual claim' a structural guarantee rather than a prompt instruction.

    `conflicting_group_id`, when set, links this claim to one or more other
    ClaimFields in the same category that disagree on the same fact (see rule
    4 in analysis_prompts.EXTRACTION_SYSTEM_PROMPT). `is_preferred`,
    `resolution_status`, and `resolution_reason` are only meaningful on
    members of such a group — they let the model record its best-effort
    resolution *without* discarding the losing value, which stays a separate
    entry with its own evidence_ids."""

    value: str
    evidence_ids: list[str] = Field(default_factory=list)
    is_inference: bool = False
    confidence: Confidence = Confidence.LOW
    is_unsupported: bool = False
    conflicting_group_id: str | None = None
    source_dates: list[str] | None = None
    is_preferred: bool = False
    resolution_status: ResolutionStatus | None = None
    resolution_reason: str | None = None

    @model_validator(mode="after")
    def _require_evidence_unless_unsupported(self) -> "ClaimField":
        unsupported = self.value == UNSUPPORTED_VALUE or self.is_unsupported
        if not unsupported and not self.evidence_ids:
            raise ValueError(
                f"Claim value {self.value!r} is not marked unsupported but has no evidence_ids"
            )
        if unsupported:
            # Normalize: an unsupported claim always looks the same regardless
            # of how the LLM phrased it.
            object.__setattr__(self, "value", UNSUPPORTED_VALUE)
            object.__setattr__(self, "is_unsupported", True)
            object.__setattr__(self, "evidence_ids", [])
        return self

    @model_validator(mode="after")
    def _downgrade_single_source_high_confidence(self) -> "ClaimField":
        # A single source can't earn "high" confidence regardless of what the
        # model claims — defensive, deterministic downgrade in Python.
        if self.confidence == Confidence.HIGH and len(self.evidence_ids) < 2:
            object.__setattr__(self, "confidence", Confidence.MEDIUM)
        return self


def unsupported_claim() -> ClaimField:
    return ClaimField(value=UNSUPPORTED_VALUE, is_unsupported=True, confidence=Confidence.LOW)


class RedFlag(BaseModel):
    """A material negative development about a competitor (price increase,
    discontinuation, security incident, layoffs, legal/regulatory issue,
    churn pattern, feature deprecation, acquisition uncertainty, ...). Emitted
    by the same extraction call as the category claims (see rule 6 in
    analysis_prompts.EXTRACTION_SYSTEM_PROMPT) since red flags are inherently
    cross-category and that call already sees evidence for every category."""

    red_flag_id: str | None = None
    type: str
    severity: Severity
    description: str
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: Confidence = Confidence.LOW

    @model_validator(mode="after")
    def _require_evidence(self) -> "RedFlag":
        if not self.evidence_ids:
            raise ValueError(f"Red flag {self.type!r} has no evidence_ids")
        return self


class ConflictingValue(BaseModel):
    value: str
    evidence_ids: list[str] = Field(default_factory=list)


class Conflict(BaseModel):
    """Group-level view of a `conflicting_group_id` cluster of ClaimFields —
    a reporting convenience assembled deterministically in Python
    (services/analysis_service.build_conflicts) from claims the model already
    produced. Never constructed by the LLM directly."""

    field: str
    values: list[ConflictingValue]
    resolution_status: ResolutionStatus = "unresolved"
    preferred_value: str | None = None
    resolution_reason: str | None = None


class ExtractedProfile(BaseModel):
    """What the LLM produces directly: just the category fields (+ red flags),
    no identity or scoring — those are assembled in Python
    (services/analysis_service.py) so the deterministic coverage score never
    depends on what the model reports."""

    company_description: list[ClaimField] = Field(default_factory=lambda: [unsupported_claim()])
    pricing: list[ClaimField] = Field(default_factory=lambda: [unsupported_claim()])
    core_features: list[ClaimField] = Field(default_factory=lambda: [unsupported_claim()])
    target_customers: list[ClaimField] = Field(default_factory=lambda: [unsupported_claim()])
    positioning: list[ClaimField] = Field(default_factory=lambda: [unsupported_claim()])
    differentiators: list[ClaimField] = Field(default_factory=lambda: [unsupported_claim()])
    announcements: list[ClaimField] = Field(default_factory=lambda: [unsupported_claim()])
    recent_news: list[ClaimField] = Field(default_factory=lambda: [unsupported_claim()])
    free_trial: list[ClaimField] = Field(default_factory=lambda: [unsupported_claim()])
    customer_reviews: list[ClaimField] = Field(default_factory=lambda: [unsupported_claim()])
    notable_customers: list[ClaimField] = Field(default_factory=lambda: [unsupported_claim()])
    red_flags: list[RedFlag] = Field(default_factory=list)


class CompetitorProfile(BaseModel):
    competitor_id: str
    competitor_name: str

    company_description: list[ClaimField] = Field(default_factory=lambda: [unsupported_claim()])
    pricing: list[ClaimField] = Field(default_factory=lambda: [unsupported_claim()])
    core_features: list[ClaimField] = Field(default_factory=lambda: [unsupported_claim()])
    target_customers: list[ClaimField] = Field(default_factory=lambda: [unsupported_claim()])
    positioning: list[ClaimField] = Field(default_factory=lambda: [unsupported_claim()])
    differentiators: list[ClaimField] = Field(default_factory=lambda: [unsupported_claim()])
    announcements: list[ClaimField] = Field(default_factory=lambda: [unsupported_claim()])
    recent_news: list[ClaimField] = Field(default_factory=lambda: [unsupported_claim()])
    free_trial: list[ClaimField] = Field(default_factory=lambda: [unsupported_claim()])
    customer_reviews: list[ClaimField] = Field(default_factory=lambda: [unsupported_claim()])
    notable_customers: list[ClaimField] = Field(default_factory=lambda: [unsupported_claim()])
    red_flags: list[RedFlag] = Field(default_factory=list)

    evidence_coverage_score: float = Field(ge=0.0, le=1.0, default=0.0)
    overall_confidence: Confidence = Confidence.LOW

    def category_fields(self) -> dict[str, list[ClaimField]]:
        return {name: getattr(self, name) for name in COVERAGE_CATEGORIES}
