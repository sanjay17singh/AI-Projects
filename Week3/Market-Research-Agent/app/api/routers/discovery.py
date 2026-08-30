from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.api.deps import get_db, get_session_factory_dep, get_settings_dep
from app.config import Settings
from app.graphs.discovery_graph import build_discovery_graph
from app.schemas.discovery import DiscoveryRequest, DiscoveryResponse, DiscoveryRunCreated
from app.services import discovery_service, run_service
from app.utils.ids import to_uuid

router = APIRouter(prefix="/api/v1/discovery", tags=["discovery"])


def _run_discovery_graph(
    run_id: str, request: DiscoveryRequest, settings: Settings, session_factory
) -> None:
    db = session_factory()
    try:
        run = run_service.get_run(db, to_uuid(run_id))
        workspace_id = str(run.workspace_id)
    finally:
        db.close()

    graph = build_discovery_graph(settings, session_factory)
    initial_state = {
        "run_id": run_id,
        "workspace_id": workspace_id,
        "target_company_name": request.target_company_name,
        "target_company_website": request.target_company_website,
        "industry": request.industry,
        "geography": request.geography,
        "customer_segment": request.customer_segment,
        "news_window_days": request.news_window_days,
        "retry_count": 0,
        "max_retries": settings.max_discovery_retries,
        "errors": [],
    }
    try:
        graph.invoke(initial_state, config={"recursion_limit": 50})
    except Exception as exc:  # noqa: BLE001 — last-resort: never leave a run stuck "pending"
        db = session_factory()
        try:
            run_service.update_status(
                db, to_uuid(run_id), "discovery_failed", error_message=str(exc)
            )
        finally:
            db.close()


@router.post("/runs", response_model=DiscoveryRunCreated, status_code=202)
def create_discovery_run(
    request: DiscoveryRequest,
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
    session_factory=Depends(get_session_factory_dep),
) -> DiscoveryRunCreated:
    workspace = run_service.ensure_default_workspace(db)
    run = run_service.create_run(db, workspace.id, request, settings.default_budget_usd_limit)

    background_tasks.add_task(_run_discovery_graph, str(run.id), request, settings, session_factory)

    return DiscoveryRunCreated(run_id=run.id)


@router.get("/runs/{run_id}", response_model=DiscoveryResponse)
def get_discovery_run(run_id: UUID, db=Depends(get_db)) -> DiscoveryResponse:
    run = run_service.get_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    candidates = discovery_service.get_candidates(db, run_id)
    return DiscoveryResponse(
        run_id=run.id,
        status=run.status,
        candidates=candidates,
        error_message=run.error_message,
    )
