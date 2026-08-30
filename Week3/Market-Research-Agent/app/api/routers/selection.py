from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.api.deps import get_checkpointer_dep, get_db, get_session_factory_dep, get_settings_dep
from app.config import Settings
from app.graphs.research_analysis_graph import build_research_analysis_graph
from app.schemas.discovery import SelectionRequest, SelectionResponse
from app.services import run_service
from app.services.selection_service import InvalidSelectionError, validate_and_persist_selection
from app.utils.ids import to_uuid

router = APIRouter(prefix="/api/v1/discovery", tags=["selection"])


def _run_research_analysis_graph(
    run_id: str, competitors: list[dict], settings: Settings, session_factory, checkpointer
) -> None:
    db = session_factory()
    try:
        run = run_service.get_run(db, to_uuid(run_id))
        workspace_id = str(run.workspace_id)
        news_window_days = run.news_window_days
        budget_usd_limit = float(run.budget_usd_limit)
    finally:
        db.close()

    graph = build_research_analysis_graph(settings, session_factory, checkpointer=checkpointer)
    initial_state = {
        "run_id": run_id,
        "workspace_id": workspace_id,
        "competitors": competitors,
        "news_window_days": news_window_days,
        "budget_usd_limit": budget_usd_limit,
        "projected_cost_usd": 0.0,
        "actual_cost_usd": 0.0,
        "approved": False,
        "research_results": [],
        "analysis_results": [],
        "retry_counts": {},
        "max_retries_per_competitor": settings.max_retries_per_competitor,
        "gap_retry_counts": {},
        "max_gap_retries": settings.max_gap_retries,
        "coverage_threshold": settings.coverage_threshold,
    }
    config = {"recursion_limit": 100, "configurable": {"thread_id": run_id}}
    try:
        graph.invoke(initial_state, config=config)
    except Exception as exc:  # noqa: BLE001 — never leave a run stuck mid-way
        db = session_factory()
        try:
            run_service.update_status(db, to_uuid(run_id), "failed", error_message=str(exc))
        finally:
            db.close()


@router.post("/runs/{run_id}/selection", response_model=SelectionResponse)
def select_competitors(
    run_id: UUID,
    request: SelectionRequest,
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
    session_factory=Depends(get_session_factory_dep),
    checkpointer=Depends(get_checkpointer_dep),
) -> SelectionResponse:
    run = run_service.get_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    try:
        selected = validate_and_persist_selection(db, run_id, request.competitor_candidate_ids)
    except InvalidSelectionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    competitors = [
        {
            "id": str(c.id),
            "name": c.company_name,
            "website": c.website,
            "classification": c.classification,
        }
        for c in selected
    ]

    background_tasks.add_task(
        _run_research_analysis_graph,
        str(run_id),
        competitors,
        settings,
        session_factory,
        checkpointer,
    )

    return SelectionResponse(run_id=run_id, status="research_running")
