"""The only module that writes runs/run_events rows — the audit-log spine
every graph node reports progress through."""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Run, RunEvent, Workspace
from app.schemas.discovery import DiscoveryRequest

DEFAULT_WORKSPACE_NAME = "default"


def ensure_default_workspace(db: Session) -> Workspace:
    existing = db.execute(
        select(Workspace).where(Workspace.name == DEFAULT_WORKSPACE_NAME)
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    workspace = Workspace(name=DEFAULT_WORKSPACE_NAME)
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return workspace


def create_run(
    db: Session, workspace_id: UUID, request: DiscoveryRequest, budget_usd_limit: float
) -> Run:
    run = Run(
        workspace_id=workspace_id,
        target_company_name=request.target_company_name,
        target_company_website=request.target_company_website,
        industry=request.industry,
        geography=request.geography,
        customer_segment=request.customer_segment,
        news_window_days=request.news_window_days,
        status="discovery_pending",
        budget_usd_limit=budget_usd_limit,
        actual_cost_usd=0,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    record_event(db, run.id, "RUN_CREATED")
    return run


def get_run(db: Session, run_id: UUID) -> Run | None:
    return db.get(Run, run_id)


def update_status(db: Session, run_id: UUID, status: str, error_message: str | None = None) -> None:
    run = db.get(Run, run_id)
    if run is None:
        return
    run.status = status
    if error_message is not None:
        run.error_message = error_message
    db.commit()


def record_event(
    db: Session,
    run_id: UUID,
    event_type: str,
    node_name: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    db.add(RunEvent(run_id=run_id, event_type=event_type, node_name=node_name, payload=payload))
    db.commit()
