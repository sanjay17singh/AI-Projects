"""Shared enums and small value objects used across schemas, DB models, and the graph state."""

from typing import Literal

ChangeType = Literal["prompt", "model", "tool", "policy", "retrieval"]

TargetConfig = Literal["vulnerable", "guarded"]

ExecutionStatus = Literal["passed", "failed", "error", "timeout", "inconclusive"]

FindingSeverity = Literal["low", "medium", "high", "critical"]

FindingStatus = Literal["open", "mitigated", "accepted"]

AssertionSource = Literal["deterministic", "llm"]

GuardrailStatus = Literal["proposed", "approved", "rejected", "applied"]

ReviewType = Literal[
    "budget",
    "guardrail",
    "release_override",
    "release",
    "regression_promotion",
    "publish",
]

ReviewStatus = Literal["pending", "decided"]

HumanDecisionValue = Literal["approve", "reject"]

ReleaseRecommendation = Literal["APPROVE", "APPROVE_WITH_CONDITIONS", "BLOCK", "INCONCLUSIVE"]

FailureClass = Literal["product", "security", "policy", "infrastructure", "evaluation_system"]

RunStatus = Literal[
    "running",
    "paused_for_human_review",
    "errored",
    "failed_closed",
    "completed",
]
