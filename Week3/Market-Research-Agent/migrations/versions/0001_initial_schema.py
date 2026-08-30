"""initial schema: workspaces, runs, discovery_candidates, competitor_selections,
research_evidence, competitor_profiles, analysis_claims, run_costs, run_events, briefings

Revision ID: 0001
Revises:
Create Date: 2026-08-29

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _uuid_pk_col() -> sa.Column:
    return sa.Column(
        "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "workspaces",
        _uuid_pk_col(),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "runs",
        _uuid_pk_col(),
        sa.Column(
            "workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id"), nullable=False
        ),
        sa.Column("target_company_name", sa.String(500), nullable=False),
        sa.Column("target_company_website", sa.String(500)),
        sa.Column("industry", sa.String(255)),
        sa.Column("geography", sa.String(255)),
        sa.Column("customer_segment", sa.String(255)),
        sa.Column("news_window_days", sa.Integer, nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="discovery_pending"),
        sa.Column("budget_usd_limit", sa.Numeric(10, 2), nullable=False, server_default="5.00"),
        sa.Column("projected_cost_usd", sa.Numeric(10, 2)),
        sa.Column("actual_cost_usd", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('discovery_pending','discovery_complete','discovery_failed',"
            "'awaiting_selection','research_running','awaiting_budget_approval',"
            "'analysis_running','compiling','complete','failed')",
            name="ck_runs_status",
        ),
    )

    op.create_table(
        "discovery_candidates",
        _uuid_pk_col(),
        sa.Column("run_id", UUID(as_uuid=True), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("company_name", sa.String(500), nullable=False),
        sa.Column("website", sa.String(500)),
        sa.Column("match_score", sa.Numeric(4, 3), nullable=False),
        sa.Column("classification", sa.String(20), nullable=False),
        sa.Column("explanation", sa.Text, nullable=False),
        sa.Column("source_urls", JSONB, nullable=False, server_default="[]"),
        sa.Column("rank", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "match_score >= 0 AND match_score <= 1", name="ck_candidate_score_range"
        ),
        sa.CheckConstraint(
            "classification IN ('direct','indirect','emerging')", name="ck_candidate_classification"
        ),
    )

    op.create_table(
        "competitor_selections",
        _uuid_pk_col(),
        sa.Column("run_id", UUID(as_uuid=True), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column(
            "discovery_candidate_id",
            UUID(as_uuid=True),
            sa.ForeignKey("discovery_candidates.id"),
            nullable=False,
        ),
        sa.Column("selected_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("selected_by", sa.String(255)),
        sa.UniqueConstraint("run_id", "discovery_candidate_id", name="uq_selection_run_candidate"),
    )

    op.create_table(
        "research_evidence",
        _uuid_pk_col(),
        sa.Column("run_id", UUID(as_uuid=True), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column(
            "competitor_id",
            UUID(as_uuid=True),
            sa.ForeignKey("discovery_candidates.id"),
            nullable=False,
        ),
        sa.Column("source_type", sa.String(10), nullable=False),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("canonical_url", sa.Text, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("title", sa.Text),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("query_used", sa.Text, nullable=False),
        sa.Column("provider", sa.String(50), nullable=False, server_default="you_com"),
        sa.Column("raw_snippet", sa.Text),
        sa.Column("http_status", sa.Integer),
        sa.Column("chunk_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("embedding_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("dedupe_of", UUID(as_uuid=True), sa.ForeignKey("research_evidence.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("source_type IN ('web','news')", name="ck_evidence_source_type"),
        sa.CheckConstraint(
            "embedding_status IN ('pending','stored','failed')", name="ck_evidence_embedding_status"
        ),
        sa.UniqueConstraint(
            "run_id",
            "competitor_id",
            "canonical_url",
            "content_hash",
            name="uq_evidence_dedupe_key",
        ),
    )

    op.create_table(
        "competitor_profiles",
        _uuid_pk_col(),
        sa.Column("run_id", UUID(as_uuid=True), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column(
            "competitor_id",
            UUID(as_uuid=True),
            sa.ForeignKey("discovery_candidates.id"),
            nullable=False,
        ),
        sa.Column("evidence_coverage_score", sa.Numeric(4, 3), nullable=False),
        sa.Column("overall_confidence", sa.String(10), nullable=False),
        sa.Column("raw_profile_json", JSONB, nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "overall_confidence IN ('high','medium','low')", name="ck_profile_confidence"
        ),
        sa.UniqueConstraint("run_id", "competitor_id", name="uq_profile_run_competitor"),
    )

    op.create_table(
        "analysis_claims",
        _uuid_pk_col(),
        sa.Column(
            "competitor_profile_id",
            UUID(as_uuid=True),
            sa.ForeignKey("competitor_profiles.id"),
            nullable=False,
        ),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("field_name", sa.String(100), nullable=False),
        sa.Column("value_text", sa.Text, nullable=False),
        sa.Column("is_inference", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("confidence", sa.String(10), nullable=False),
        sa.Column("evidence_ids", JSONB, nullable=False, server_default="[]"),
        sa.Column("is_unsupported", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("conflicting_group_id", sa.String(64)),
        sa.Column("source_dates", JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("confidence IN ('high','medium','low')", name="ck_claim_confidence"),
    )

    op.create_table(
        "run_costs",
        _uuid_pk_col(),
        sa.Column("run_id", UUID(as_uuid=True), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("node_name", sa.String(100), nullable=False),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("unit_type", sa.String(30), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("unit_cost_usd", sa.Numeric(14, 8), nullable=False),
        sa.Column("cost_usd", sa.Numeric(10, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("provider IN ('openai','you_com','pinecone')", name="ck_cost_provider"),
        sa.CheckConstraint(
            "unit_type IN ('tokens_in','tokens_out','api_call','embedding_tokens')",
            name="ck_cost_unit_type",
        ),
    )

    op.create_table(
        "run_events",
        _uuid_pk_col(),
        sa.Column("run_id", UUID(as_uuid=True), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("node_name", sa.String(100)),
        sa.Column("payload", JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "briefings",
        _uuid_pk_col(),
        sa.Column("run_id", UUID(as_uuid=True), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("markdown_content", sa.Text, nullable=False),
        sa.Column("coverage_summary", JSONB, nullable=False, server_default="{}"),
        sa.Column("unresolved_conflicts", JSONB, nullable=False, server_default="[]"),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("run_id", name="uq_briefing_run"),
    )


def downgrade() -> None:
    op.drop_table("briefings")
    op.drop_table("run_events")
    op.drop_table("run_costs")
    op.drop_table("analysis_claims")
    op.drop_table("competitor_profiles")
    op.drop_table("research_evidence")
    op.drop_table("competitor_selections")
    op.drop_table("discovery_candidates")
    op.drop_table("runs")
    op.drop_table("workspaces")
