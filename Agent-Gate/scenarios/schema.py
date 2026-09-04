"""Pydantic schema for the version-controlled scenario catalog.

Every YAML file under scenarios/{adversarial,benign,resilience}/ must validate
against ScenarioDefinition. This is the single source of truth for what a
scenario is allowed to contain — the loader in catalog.py rejects anything
that doesn't fit.
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

ScenarioBucket = Literal["adversarial", "benign", "resilience"]

ScenarioCategory = Literal[
    # adversarial (4 each)
    "adversarial_direct_injection",
    "adversarial_indirect_injection",
    "adversarial_cross_customer",
    "adversarial_unauthorized_refund",
    # benign (2 each)
    "benign_lookup",
    "benign_low_value_refund",
    "benign_escalation_refund",
    "benign_kb_question",
    "benign_data_correction",
    "benign_ticket_creation",
    "benign_unavailable_info",
    "benign_safe_refusal",
    # resilience (1 each)
    "resilience_budget_approval",
    "resilience_guardrail_approval",
    "resilience_guardrail_rejection",
    "resilience_checkpoint_recovery",
    "resilience_duplicate_decision",
    "resilience_pinecone_outage",
    "resilience_postgres_failure",
    "resilience_openai_failure",
]

RiskLevel = Literal["low", "medium", "high", "critical"]

AssertionType = Literal[
    "tool_not_called",
    "tool_called",
    "tool_called_with_constraint",
    "no_cross_customer_field_access",
    "output_excludes_pattern",
    "output_includes_pattern",
    "identity_verified_before_action",
    "requires_human_approval_flag_set",
    "no_exception_raised",
    "workflow_status_equals",
]


class AssertionSpec(BaseModel):
    """A single machine-checkable, deterministic assertion.

    `type` must be a registered assertion type (app/policy/deterministic_rules.py
    owns the implementation registry) — an unknown type fails scenario validation
    rather than silently no-op'ing at execution time.
    """

    type: AssertionType
    tool: str | None = None
    field: str | None = None
    pattern: str | None = None
    constraint: str | None = None
    expected: str | None = None
    description: str = ""


class ChatMessageSpec(BaseModel):
    role: Literal["user", "system"]
    content: str


class RetrievedDocumentSpec(BaseModel):
    doc_id: str
    title: str
    content: str
    trusted: bool = False


class ScenarioDefinition(BaseModel):
    id: str = Field(pattern=r"^[A-Z0-9][A-Z0-9\-]{2,63}$")
    title: str
    bucket: ScenarioBucket
    category: ScenarioCategory
    risk_level: RiskLevel
    description: str
    setup: dict = Field(default_factory=dict)
    input_messages: list[ChatMessageSpec]
    retrieved_context: list[RetrievedDocumentSpec] = Field(default_factory=list)
    available_tools: list[str]
    expected_behavior: str
    forbidden_behavior: str
    deterministic_assertions: list[AssertionSpec] = Field(min_length=1)
    llm_rubric: str | None = None
    tags: list[str] = Field(default_factory=list)

    @field_validator("category")
    @classmethod
    def category_matches_bucket(cls, v: str, info) -> str:
        bucket = info.data.get("bucket")
        if bucket and not v.startswith(f"{bucket}_"):
            raise ValueError(f"category '{v}' does not belong to bucket '{bucket}'")
        return v
