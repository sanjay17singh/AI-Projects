"""Research-side nodes for Graph #2. Each takes (state, deps); deps bound via
functools.partial when the graph is built (see research_analysis_graph.py)."""

from dataclasses import dataclass

from app.agents.analysis_agent import AnalysisVerificationAgent
from app.agents.orchestrator_support import latest_by_key
from app.agents.web_research_agent import WebResearchAgent
from app.schemas.common import ALL_PROFILE_CATEGORIES
from app.schemas.graph_state import ResearchGraphState
from app.schemas.research import WebResearchResult
from app.services import cost_service, run_service
from app.services.analysis_service import upsert_profile
from app.utils.ids import to_uuid


@dataclass
class ResearchDeps:
    web_research_agent: WebResearchAgent
    analysis_agent: AnalysisVerificationAgent
    session_factory: object  # Callable[[], Session]


def plan_research_node(state: ResearchGraphState, deps: ResearchDeps) -> dict:
    db = deps.session_factory()
    try:
        run_id = to_uuid(state["run_id"])
        provider_count = len(deps.web_research_agent.provider_names)
        projected = cost_service.project_cost(
            len(state.get("competitors", [])), search_provider_count=provider_count
        )
        run = run_service.get_run(db, run_id)
        if run is not None:
            run.projected_cost_usd = projected
            db.commit()
        run_service.record_event(
            db, run_id, "RESEARCH_PLANNED", payload={"projected_cost_usd": projected}
        )
    finally:
        db.close()
    return {
        "projected_cost_usd": projected,
        "actual_cost_usd": 0.0,
        "research_results": [],
        "analysis_results": [],
        "retry_counts": {},
        "gap_retry_counts": {},
    }


def request_budget_approval_node(state: ResearchGraphState, deps: ResearchDeps) -> dict:
    db = deps.session_factory()
    try:
        run_id = to_uuid(state["run_id"])
        run_service.update_status(db, run_id, "awaiting_budget_approval")
        run_service.record_event(
            db,
            run_id,
            "BUDGET_EXCEEDED",
            payload={
                "projected_cost_usd": state.get("projected_cost_usd"),
                "budget_usd_limit": state.get("budget_usd_limit"),
            },
        )
        run_service.record_event(db, run_id, "HUMAN_APPROVAL_REQUESTED")
    finally:
        db.close()
    return {"status": "awaiting_budget_approval"}


def web_research_node(state: ResearchGraphState, deps: ResearchDeps) -> dict:
    competitor = state["_target_competitor"]
    db = deps.session_factory()
    try:
        run_id = to_uuid(state["run_id"])
        competitor_id = to_uuid(competitor["id"])
        try:
            result = deps.web_research_agent.research(
                db=db,
                run_id=run_id,
                workspace_id=state["workspace_id"],
                competitor_id=competitor_id,
                competitor_name=competitor["name"],
                news_window_days=state["news_window_days"],
            )
        except Exception as exc:  # noqa: BLE001 — a branch failing must never crash the run
            result = WebResearchResult(
                competitor_id=str(competitor_id), failed=True, failures=[str(exc)]
            )
        if result.categories_covered:
            for provider in deps.web_research_agent.provider_names:
                cost_service.record_cost(
                    db,
                    run_id,
                    "web_research_node",
                    provider,
                    "api_call",
                    len(result.categories_covered),
                )
    finally:
        db.close()
    return {"research_results": [result.model_dump(mode="json")]}


def research_join_node(state: ResearchGraphState, deps: ResearchDeps) -> dict:
    """Bookkeeping: increments retry_counts for competitors whose latest
    attempt failed, and logs a permanent-failure event once retries for that
    competitor are exhausted (so the status endpoint can report it without
    inspecting live graph state). Runs once after all concurrent
    web_research_node branches converge here — one writer per state update,
    no concurrent-write conflicts on the plain, non-reducer retry_counts dict."""
    latest = latest_by_key(state.get("research_results", []))
    retry_counts = dict(state.get("retry_counts", {}))
    max_retries = state.get("max_retries_per_competitor", 2)
    newly_permanent_failures = []
    for competitor_id, result in latest.items():
        if result.get("failed"):
            retry_counts[competitor_id] = retry_counts.get(competitor_id, 0) + 1
            if retry_counts[competitor_id] >= max_retries:
                newly_permanent_failures.append(competitor_id)

    if newly_permanent_failures:
        db = deps.session_factory()
        try:
            run_id = to_uuid(state["run_id"])
            for competitor_id in newly_permanent_failures:
                run_service.record_event(
                    db,
                    run_id,
                    "COMPETITOR_PERMANENTLY_FAILED",
                    node_name="research_join_node",
                    payload={"competitor_id": competitor_id},
                )
        finally:
            db.close()

    return {"retry_counts": retry_counts}


def gap_research_node(state: ResearchGraphState, deps: ResearchDeps) -> dict:
    """Targeted re-research for one under-covered competitor: fetches more
    evidence for its missing categories, then re-runs analysis so the profile
    incorporates it. Feeds back into analysis_results (same shape as
    analysis_node) so it rejoins the normal coverage-check cycle."""
    competitor = state["_target_competitor"]
    db = deps.session_factory()
    try:
        run_id = to_uuid(state["run_id"])
        competitor_id = to_uuid(competitor["id"])
        latest_analysis = latest_by_key(state.get("analysis_results", [])).get(competitor["id"], {})
        missing_categories = [
            category
            for category in ALL_PROFILE_CATEGORIES
            if all(
                claim.get("is_unsupported")
                for claim in latest_analysis.get(category, [{"is_unsupported": True}])
            )
        ]
        if missing_categories:
            try:
                deps.web_research_agent.research(
                    db=db,
                    run_id=run_id,
                    workspace_id=state["workspace_id"],
                    competitor_id=competitor_id,
                    competitor_name=competitor["name"],
                    news_window_days=state["news_window_days"],
                    categories=missing_categories,
                )
            except Exception:  # noqa: BLE001 — gap research is best-effort
                pass

        profile = deps.analysis_agent.analyze(
            workspace_id=state["workspace_id"],
            run_id=run_id,
            competitor_id=competitor_id,
            competitor_name=competitor["name"],
        )
        upsert_profile(db, run_id, competitor_id, profile)
    finally:
        db.close()
    return {"analysis_results": [profile.model_dump(mode="json")]}
