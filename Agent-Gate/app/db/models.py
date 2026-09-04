"""SQLAlchemy models — the authoritative system of record.

Deliberately kept logically separate from the LangGraph checkpoint tables
(created independently by langgraph-checkpoint-postgres's own setup()) so
audit/business data and workflow-replay data never share migration history.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class ProposedChangeModel(Base):
    __tablename__ = "proposed_changes"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String, nullable=False, default="default")
    change_type: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    diff_summary: Mapped[str] = mapped_column(Text, nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    runs: Mapped[list["EvaluationRunModel"]] = relationship(back_populates="change")


class EvaluationRunModel(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    change_id: Mapped[str] = mapped_column(ForeignKey("proposed_changes.id"), nullable=False)
    thread_id: Mapped[str] = mapped_column(String, nullable=False, unique=True, default=_uuid)
    status: Mapped[str] = mapped_column(String, nullable=False, default="running")
    scenario_budget: Mapped[int] = mapped_column(Integer, nullable=False)
    budget_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    coverage_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    semantic_coverage_degraded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    release_decision: Mapped[str | None] = mapped_column(String, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    change: Mapped["ProposedChangeModel"] = relationship(back_populates="runs")


class ScenarioDefinitionModel(Base):
    __tablename__ = "scenario_definitions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    category: Mapped[str] = mapped_column(String, nullable=False)
    bucket: Mapped[str] = mapped_column(String, nullable=False)
    risk_level: Mapped[str] = mapped_column(String, nullable=False)
    schema_version: Mapped[str] = mapped_column(String, nullable=False, default="1.0")
    definition: Mapped[dict] = mapped_column(JSON, nullable=False)
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ScenarioExecutionModel(Base):
    __tablename__ = "scenario_executions"
    __table_args__ = (
        UniqueConstraint("run_id", "scenario_id", "attempt", name="uq_execution_attempt"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("evaluation_runs.id"), nullable=False)
    scenario_id: Mapped[str] = mapped_column(String, nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    target_config: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    transcript: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    tool_calls: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    final_output: Mapped[str] = mapped_column(Text, nullable=False, default="")
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class FindingModel(Base):
    __tablename__ = "findings"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("evaluation_runs.id"), nullable=False)
    scenario_execution_id: Mapped[str] = mapped_column(
        ForeignKey("scenario_executions.id"), nullable=False
    )
    scenario_id: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    assertion_source: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class EvidenceModel(Base):
    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    finding_id: Mapped[str | None] = mapped_column(ForeignKey("findings.id"), nullable=True)
    scenario_execution_id: Mapped[str | None] = mapped_column(
        ForeignKey("scenario_executions.id"), nullable=True
    )
    evidence_type: Mapped[str] = mapped_column(String, nullable=False)
    redacted_content: Mapped[dict] = mapped_column(JSON, nullable=False)
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class GuardrailRecommendationModel(Base):
    __tablename__ = "guardrail_recommendations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("evaluation_runs.id"), nullable=False)
    finding_id: Mapped[str] = mapped_column(ForeignKey("findings.id"), nullable=False)
    failure_summary: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_change: Mapped[str] = mapped_column(Text, nullable=False)
    benefit: Mapped[str] = mapped_column(Text, nullable=False)
    side_effects: Mapped[str] = mapped_column(Text, nullable=False)
    validation_scenarios: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    rollback_guidance: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="proposed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class HumanReviewRequestModel(Base):
    __tablename__ = "human_review_requests"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("evaluation_runs.id"), nullable=False)
    review_type: Mapped[str] = mapped_column(String, nullable=False)
    evidence_ref: Mapped[str] = mapped_column(String, nullable=False)
    available_actions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    idempotency_key: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class HumanDecisionModel(Base):
    __tablename__ = "human_decisions"
    __table_args__ = (
        UniqueConstraint("review_request_id", name="uq_one_decision_per_request"),
        CheckConstraint("length(justification) > 0", name="ck_justification_required"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    review_request_id: Mapped[str] = mapped_column(
        ForeignKey("human_review_requests.id"), nullable=False
    )
    reviewer: Mapped[str] = mapped_column(String, nullable=False)
    decision: Mapped[str] = mapped_column(String, nullable=False)
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ReleaseDecisionModel(Base):
    __tablename__ = "release_decisions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("evaluation_runs.id"), nullable=False)
    recommendation: Mapped[str] = mapped_column(String, nullable=False)
    decided_by: Mapped[str] = mapped_column(String, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class RegressionTestModel(Base):
    __tablename__ = "regression_tests"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    origin_finding_id: Mapped[str] = mapped_column(ForeignKey("findings.id"), nullable=False)
    origin_run_id: Mapped[str] = mapped_column(ForeignKey("evaluation_runs.id"), nullable=False)
    scenario_definition: Mapped[dict] = mapped_column(JSON, nullable=False)
    dedup_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    approval_status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    idempotency_key: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AuditEventModel(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    run_id: Mapped[str | None] = mapped_column(String, nullable=True)
    actor: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    correlation_id: Mapped[str] = mapped_column(String, nullable=False)
    input_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    output_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    state_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    event_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
