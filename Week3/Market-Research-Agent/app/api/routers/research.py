from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select

from app.api.deps import get_checkpointer_dep, get_db, get_session_factory_dep, get_settings_dep
from app.config import Settings
from app.db.models import CompetitorProfile as CompetitorProfileRow
from app.db.models import CompetitorSelection, DiscoveryCandidate, ResearchEvidence, RunEvent
from app.graphs.research_analysis_graph import build_research_analysis_graph
from app.services import run_service
from app.utils.ids import to_uuid

router = APIRouter(prefix="/api/v1/research", tags=["research"])


class ApproveBudgetRequest(BaseModel):
    new_budget_usd_limit: float


class CompetitorStatus(BaseModel):
    id: UUID
    name: str
    phase: str
    evidence_count: int


class BudgetStatus(BaseModel):
    projected: float | None
    actual: float
    limit: float
    awaiting_approval: bool


class ResearchStatusResponse(BaseModel):
    run_id: UUID
    status: str
    competitors: list[CompetitorStatus]
    budget: BudgetStatus


def _competitor_phase(
    competitor_id: UUID,
    has_profile: bool,
    evidence_count: int,
    permanently_failed_ids: set[str],
    run_status: str,
) -> str:
    if has_profile:
        return "complete"
    if str(competitor_id) in permanently_failed_ids:
        return "failed"
    if evidence_count > 0:
        return "analyzing"
    if run_status == "awaiting_budget_approval":
        return "queued"
    return "researching"


@router.get("/runs/{run_id}/status", response_model=ResearchStatusResponse)
def get_research_status(run_id: UUID, db=Depends(get_db)) -> ResearchStatusResponse:
    run = run_service.get_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    selected = list(
        db.execute(
            select(DiscoveryCandidate)
            .join(
                CompetitorSelection,
                CompetitorSelection.discovery_candidate_id == DiscoveryCandidate.id,
            )
            .where(CompetitorSelection.run_id == run_id)
        ).scalars()
    )

    profile_ids = {
        row.competitor_id
        for row in db.execute(
            select(CompetitorProfileRow.competitor_id).where(CompetitorProfileRow.run_id == run_id)
        )
    }

    evidence_counts = dict(
        db.execute(
            select(ResearchEvidence.competitor_id, func.count(ResearchEvidence.id))
            .where(ResearchEvidence.run_id == run_id)
            .group_by(ResearchEvidence.competitor_id)
        ).all()
    )

    permanently_failed_ids = {
        row.payload.get("competitor_id")
        for row in db.execute(
            select(RunEvent).where(
                RunEvent.run_id == run_id, RunEvent.event_type == "COMPETITOR_PERMANENTLY_FAILED"
            )
        ).scalars()
        if row.payload
    }

    competitors = [
        CompetitorStatus(
            id=c.id,
            name=c.company_name,
            phase=_competitor_phase(
                c.id,
                c.id in profile_ids,
                evidence_counts.get(c.id, 0),
                permanently_failed_ids,
                run.status,
            ),
            evidence_count=evidence_counts.get(c.id, 0),
        )
        for c in selected
    ]

    budget = BudgetStatus(
        projected=float(run.projected_cost_usd) if run.projected_cost_usd is not None else None,
        actual=float(run.actual_cost_usd or 0),
        limit=float(run.budget_usd_limit),
        awaiting_approval=run.status == "awaiting_budget_approval",
    )

    return ResearchStatusResponse(
        run_id=run.id, status=run.status, competitors=competitors, budget=budget
    )


def _resume_research_analysis_graph(
    run_id: str, new_budget_usd_limit: float, settings: Settings, session_factory, checkpointer
) -> None:
    graph = build_research_analysis_graph(settings, session_factory, checkpointer=checkpointer)
    resume_update = {"approved": True, "budget_usd_limit": new_budget_usd_limit}
    config = {"recursion_limit": 100, "configurable": {"thread_id": run_id}}
    try:
        graph.invoke(resume_update, config=config)
    except Exception as exc:  # noqa: BLE001 — never leave a run stuck mid-way
        db = session_factory()
        try:
            run_service.update_status(db, to_uuid(run_id), "failed", error_message=str(exc))
        finally:
            db.close()


@router.post("/runs/{run_id}/approve-budget", response_model=ResearchStatusResponse)
def approve_budget(
    run_id: UUID,
    request: ApproveBudgetRequest,
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
    session_factory=Depends(get_session_factory_dep),
    checkpointer=Depends(get_checkpointer_dep),
) -> ResearchStatusResponse:
    run = run_service.get_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status != "awaiting_budget_approval":
        raise HTTPException(
            status_code=409, detail=f"Run is not awaiting budget approval (status={run.status})"
        )

    run.budget_usd_limit = request.new_budget_usd_limit
    db.commit()
    run_service.record_event(
        db,
        run_id,
        "HUMAN_APPROVAL_GRANTED",
        payload={"new_budget_usd_limit": request.new_budget_usd_limit},
    )

    background_tasks.add_task(
        _resume_research_analysis_graph,
        str(run_id),
        request.new_budget_usd_limit,
        settings,
        session_factory,
        checkpointer,
    )

    return get_research_status(run_id, db=db)
