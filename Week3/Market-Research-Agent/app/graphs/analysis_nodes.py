from app.agents.orchestrator_support import latest_by_key
from app.graphs.research_nodes import ResearchDeps
from app.schemas.graph_state import ResearchGraphState
from app.services import cost_service, export_service, run_service
from app.services.analysis_service import persist_profile
from app.services.cost_service import AVG_EXTRACTION_TOKENS_IN, AVG_EXTRACTION_TOKENS_OUT
from app.utils.ids import to_uuid


def analysis_node(state: ResearchGraphState, deps: ResearchDeps) -> dict:
    competitor = state["_target_competitor"]
    db = deps.session_factory()
    try:
        run_id = to_uuid(state["run_id"])
        competitor_id = to_uuid(competitor["id"])
        profile = deps.analysis_agent.analyze(
            workspace_id=state["workspace_id"],
            run_id=run_id,
            competitor_id=competitor_id,
            competitor_name=competitor["name"],
        )
        persist_profile(db, run_id, competitor_id, profile)
        # Prefer real token usage from the extraction call (last_usage is
        # populated on a best-effort basis in AnalysisVerificationAgent._extract
        # via include_raw=True); fall back to the rough per-category averages
        # when a model/fake didn't report usage_metadata.
        usage = getattr(deps.analysis_agent, "last_usage", {}) or {}
        cost_service.record_cost(
            db,
            run_id,
            "analysis_node",
            "openai",
            "tokens_in",
            usage.get("tokens_in") or AVG_EXTRACTION_TOKENS_IN,
        )
        cost_service.record_cost(
            db,
            run_id,
            "analysis_node",
            "openai",
            "tokens_out",
            usage.get("tokens_out") or AVG_EXTRACTION_TOKENS_OUT,
        )
    finally:
        db.close()
    return {"analysis_results": [profile.model_dump(mode="json")]}


def analysis_join_node(state: ResearchGraphState, deps: ResearchDeps) -> dict:
    """Pure bookkeeping counterpart to research_join_node: increments
    gap_retry_counts for competitors whose latest profile is still under the
    coverage threshold. No DB access, no LLM calls."""
    latest = latest_by_key(state.get("analysis_results", []))
    gap_retry_counts = dict(state.get("gap_retry_counts", {}))
    threshold = state.get("coverage_threshold", 0.6)
    for competitor_id, result in latest.items():
        if result.get("evidence_coverage_score", 0) < threshold:
            gap_retry_counts[competitor_id] = gap_retry_counts.get(competitor_id, 0) + 1
    return {"gap_retry_counts": gap_retry_counts}


def compile_briefing_node(state: ResearchGraphState, deps: ResearchDeps) -> dict:
    db = deps.session_factory()
    try:
        run_id = to_uuid(state["run_id"])
        run_service.update_status(db, run_id, "compiling")
        export_service.compile_and_persist_briefing(db, run_id)
    finally:
        db.close()
    return {"status": "compiling"}


def finalize_run_node(state: ResearchGraphState, deps: ResearchDeps) -> dict:
    db = deps.session_factory()
    try:
        run_id = to_uuid(state["run_id"])
        run_service.update_status(db, run_id, "complete")
        run_service.record_event(db, run_id, "RUN_COMPLETE")
    finally:
        db.close()
    return {"status": "complete"}


def fail_run_node(state: ResearchGraphState, deps: ResearchDeps) -> dict:
    db = deps.session_factory()
    try:
        run_id = to_uuid(state["run_id"])
        run_service.update_status(
            db,
            run_id,
            "failed",
            error_message="All competitor research branches failed permanently.",
        )
        run_service.record_event(db, run_id, "ERROR", payload={"message": "all branches failed"})
    finally:
        db.close()
    return {"status": "failed"}
