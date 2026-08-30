import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, Uuid

from app.db.base import Base

# Portable JSON column: JSONB on Postgres, plain JSON (SQLite/others) in tests.
JSONVariant = JSON().with_variant(JSONB(), "postgresql")


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Run(Base):
    __tablename__ = "runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('discovery_pending','discovery_complete','discovery_failed',"
            "'awaiting_selection','research_running','awaiting_budget_approval',"
            "'analysis_running','compiling','complete','failed')",
            name="ck_runs_status",
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)

    target_company_name: Mapped[str] = mapped_column(String(500), nullable=False)
    target_company_website: Mapped[str | None] = mapped_column(String(500))
    industry: Mapped[str | None] = mapped_column(String(255))
    geography: Mapped[str | None] = mapped_column(String(255))
    customer_segment: Mapped[str | None] = mapped_column(String(255))
    news_window_days: Mapped[int] = mapped_column(Integer, nullable=False)

    status: Mapped[str] = mapped_column(String(40), nullable=False, default="discovery_pending")

    budget_usd_limit: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=5.00)
    projected_cost_usd: Mapped[float | None] = mapped_column(Numeric(10, 2))
    actual_cost_usd: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)

    error_message: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    discovery_candidates: Mapped[list["DiscoveryCandidate"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class DiscoveryCandidate(Base):
    __tablename__ = "discovery_candidates"
    __table_args__ = (
        CheckConstraint("match_score >= 0 AND match_score <= 1", name="ck_candidate_score_range"),
        CheckConstraint(
            "classification IN ('direct','indirect','emerging')", name="ck_candidate_classification"
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runs.id"), nullable=False)

    company_name: Mapped[str] = mapped_column(String(500), nullable=False)
    website: Mapped[str | None] = mapped_column(String(500))
    match_score: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    classification: Mapped[str] = mapped_column(String(20), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    source_urls: Mapped[list] = mapped_column(JSONVariant, nullable=False, default=list)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    run: Mapped["Run"] = relationship(back_populates="discovery_candidates")


class CompetitorSelection(Base):
    __tablename__ = "competitor_selections"
    __table_args__ = (
        UniqueConstraint("run_id", "discovery_candidate_id", name="uq_selection_run_candidate"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runs.id"), nullable=False)
    discovery_candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("discovery_candidates.id"), nullable=False
    )
    selected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    selected_by: Mapped[str | None] = mapped_column(String(255))


class ResearchEvidence(Base):
    __tablename__ = "research_evidence"
    __table_args__ = (
        CheckConstraint("source_type IN ('web','news')", name="ck_evidence_source_type"),
        CheckConstraint(
            "embedding_status IN ('pending','stored','failed')", name="ck_evidence_embedding_status"
        ),
        UniqueConstraint(
            "run_id",
            "competitor_id",
            "canonical_url",
            "content_hash",
            name="uq_evidence_dedupe_key",
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runs.id"), nullable=False)
    competitor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("discovery_candidates.id"), nullable=False
    )

    source_type: Mapped[str] = mapped_column(String(10), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    query_used: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="you_com")
    raw_snippet: Mapped[str | None] = mapped_column(Text)
    http_status: Mapped[int | None] = mapped_column(Integer)

    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    embedding_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    dedupe_of: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("research_evidence.id"))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class CompetitorProfile(Base):
    __tablename__ = "competitor_profiles"
    __table_args__ = (
        CheckConstraint(
            "overall_confidence IN ('high','medium','low')", name="ck_profile_confidence"
        ),
        UniqueConstraint("run_id", "competitor_id", name="uq_profile_run_competitor"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runs.id"), nullable=False)
    competitor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("discovery_candidates.id"), nullable=False
    )

    evidence_coverage_score: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    overall_confidence: Mapped[str] = mapped_column(String(10), nullable=False)
    raw_profile_json: Mapped[dict] = mapped_column(JSONVariant, nullable=False)

    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    claims: Mapped[list["AnalysisClaim"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )


class AnalysisClaim(Base):
    __tablename__ = "analysis_claims"
    __table_args__ = (
        CheckConstraint("confidence IN ('high','medium','low')", name="ck_claim_confidence"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    competitor_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("competitor_profiles.id"), nullable=False
    )

    category: Mapped[str] = mapped_column(String(50), nullable=False)
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    value_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_inference: Mapped[bool] = mapped_column(default=False)
    confidence: Mapped[str] = mapped_column(String(10), nullable=False)
    evidence_ids: Mapped[list] = mapped_column(JSONVariant, nullable=False, default=list)
    is_unsupported: Mapped[bool] = mapped_column(default=False)
    conflicting_group_id: Mapped[str | None] = mapped_column(String(64))
    source_dates: Mapped[dict | None] = mapped_column(JSONVariant)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    profile: Mapped["CompetitorProfile"] = relationship(back_populates="claims")


class RunCost(Base):
    __tablename__ = "run_costs"
    __table_args__ = (
        CheckConstraint(
            "provider IN ('openai','you_com','pinecone','serper')", name="ck_cost_provider"
        ),
        CheckConstraint(
            "unit_type IN ('tokens_in','tokens_out','api_call','embedding_tokens')",
            name="ck_cost_unit_type",
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runs.id"), nullable=False)
    node_name: Mapped[str] = mapped_column(String(100), nullable=False)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    unit_type: Mapped[str] = mapped_column(String(30), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)
    unit_cost_usd: Mapped[float] = mapped_column(Numeric(14, 8), nullable=False)
    cost_usd: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class RunEvent(Base):
    __tablename__ = "run_events"

    id: Mapped[uuid.UUID] = _uuid_pk()
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runs.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    node_name: Mapped[str | None] = mapped_column(String(100))
    payload: Mapped[dict | None] = mapped_column(JSONVariant)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Briefing(Base):
    __tablename__ = "briefings"
    __table_args__ = (UniqueConstraint("run_id", name="uq_briefing_run"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runs.id"), nullable=False)
    markdown_content: Mapped[str] = mapped_column(Text, nullable=False)
    coverage_summary: Mapped[dict] = mapped_column(JSONVariant, nullable=False, default=dict)
    unresolved_conflicts: Mapped[list] = mapped_column(JSONVariant, nullable=False, default=list)

    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
