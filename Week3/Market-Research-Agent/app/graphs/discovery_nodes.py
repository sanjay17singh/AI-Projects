"""Discovery graph nodes. Each takes (state, deps) — deps is bound via
functools.partial when the graph is built (see discovery_graph.py) so nodes
stay plain, testable functions rather than reaching for globals."""

from dataclasses import dataclass

from app.agents.discovery_agent import DiscoveryAgent
from app.clients.youcom_client import YouComClientError
from app.schemas.discovery import CompetitorCandidate
from app.schemas.graph_state import DiscoveryGraphState
from app.services import discovery_service, run_service
from app.utils.ids import to_uuid


@dataclass
class DiscoveryDeps:
    agent: DiscoveryAgent
    session_factory: object  # Callable[[], Session] — typed loosely to avoid a hard import cycle


def normalize_request_node(state: DiscoveryGraphState, deps: DiscoveryDeps) -> dict:
    raw_request = {
        "target_company_name": state["target_company_name"],
        "target_company_website": state.get("target_company_website"),
        "industry": state.get("industry"),
        "geography": state.get("geography"),
        "customer_segment": state.get("customer_segment"),
        "news_window_days": state["news_window_days"],
    }
    try:
        normalized = deps.agent.normalize_request(raw_request)
        return {"normalized_request": normalized.model_dump(), "errors": []}
    except Exception as exc:  # noqa: BLE001 — LLM-call failure, not a bug to crash on
        return {"errors": [f"normalize_request: {exc}"]}


def generate_search_queries_node(state: DiscoveryGraphState, deps: DiscoveryDeps) -> dict:
    previous_error = (state.get("errors") or [None])[-1]
    try:
        queries = deps.agent.generate_queries(state["normalized_request"], previous_error)
        return {"search_queries": queries, "errors": []}
    except Exception as exc:  # noqa: BLE001
        return {"errors": [f"generate_search_queries: {exc}"]}


def call_youcom_search_node(state: DiscoveryGraphState, deps: DiscoveryDeps) -> dict:
    try:
        raw_results = deps.agent.search(state["search_queries"])
        return {"raw_search_results": raw_results, "errors": []}
    except YouComClientError as exc:
        return {"errors": [f"call_youcom_search: {exc}"], "raw_search_results": []}


def record_search_retry_node(state: DiscoveryGraphState, deps: DiscoveryDeps) -> dict:
    """The one place retry_count is incremented — kept out of edges.py so
    routing functions stay pure and never mutate state themselves."""
    return {"retry_count": state.get("retry_count", 0) + 1, "errors": []}


def score_and_classify_candidates_node(state: DiscoveryGraphState, deps: DiscoveryDeps) -> dict:
    try:
        candidates: list[CompetitorCandidate] = deps.agent.score_candidates(
            state["normalized_request"], state["raw_search_results"]
        )
        return {"candidates": [c.model_dump(mode="json") for c in candidates], "errors": []}
    except Exception as exc:  # noqa: BLE001
        return {"errors": [f"score_and_classify_candidates: {exc}"]}


def persist_candidates_node(state: DiscoveryGraphState, deps: DiscoveryDeps) -> dict:
    session_factory = deps.session_factory
    db = session_factory()
    try:
        candidates = [CompetitorCandidate(**c) for c in state["candidates"]]
        run_id = to_uuid(state["run_id"])
        discovery_service.persist_candidates(db, run_id, candidates)
        run_service.update_status(db, run_id, "discovery_complete")
        run_service.record_event(db, run_id, "DISCOVERY_COMPLETE")
    finally:
        db.close()
    return {"status": "discovery_complete"}


def handle_failure_node(state: DiscoveryGraphState, deps: DiscoveryDeps) -> dict:
    session_factory = deps.session_factory
    db = session_factory()
    try:
        last_error = (state.get("errors") or ["unknown error"])[-1]
        run_id = to_uuid(state["run_id"])
        run_service.update_status(db, run_id, "discovery_failed", error_message=last_error)
        run_service.record_event(db, run_id, "ERROR", payload={"message": last_error})
    finally:
        db.close()
    return {"status": "discovery_failed"}
