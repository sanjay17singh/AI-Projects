"""Every conditional-edge function for both graphs lives here, as a plain
function of state fields. No LLM calls, no I/O, nothing non-deterministic —
this file is the literal proof that routing (retries, budgets, approvals,
completion) is never left to an LLM to decide.

Edges only ROUTE; they never mutate state. Counters (retry_count,
retry_counts, gap_retry_counts) are incremented by dedicated nodes
(record_search_retry_node, research_join_node, analysis_join_node) that run
immediately before these functions are evaluated.
"""

from typing import Literal

from langgraph.types import Send

from app.agents.orchestrator_support import (
    competitors_needing_gap_research,
    competitors_needing_research_retry,
    is_over_budget,
    successful_competitor_ids,
)
from app.schemas.graph_state import DiscoveryGraphState, ResearchGraphState

# --------------------------------------------------------------------------
# Discovery graph
# --------------------------------------------------------------------------


def edge_after_search(
    state: DiscoveryGraphState,
) -> Literal["record_search_retry", "handle_failure", "score_and_classify_candidates"]:
    errors = state.get("errors") or []
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)
    if errors and retry_count < max_retries:
        return "record_search_retry"
    if errors:
        return "handle_failure"
    return "score_and_classify_candidates"


def edge_after_scoring(
    state: DiscoveryGraphState,
) -> Literal["record_search_retry", "persist_candidates"]:
    candidates = state.get("candidates") or []
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)
    errors = state.get("errors") or []
    if (len(candidates) < 5 or errors) and retry_count < max_retries:
        return "record_search_retry"
    return "persist_candidates"


# --------------------------------------------------------------------------
# Research + Analysis graph
# --------------------------------------------------------------------------


def edge_budget_check(
    state: ResearchGraphState,
) -> Literal["request_budget_approval"] | list[Send]:
    """Used as the conditional edge from BOTH plan_research and
    request_budget_approval — on resume after approval, the same function
    re-evaluates with the now-updated budget/approved fields."""
    over_budget = is_over_budget(
        state.get("projected_cost_usd", 0.0),
        state.get("actual_cost_usd", 0.0),
        state.get("budget_usd_limit", 0.0),
    )
    if over_budget and not state.get("approved"):
        return "request_budget_approval"
    return [
        Send("web_research_node", {**state, "_target_competitor": competitor})
        for competitor in state.get("competitors", [])
    ]


def edge_research_retry(state: ResearchGraphState) -> list[Send] | None:
    """None means 'no retries needed' — the caller falls through to the
    partial-failure / fan-out-to-analysis decision."""
    max_retries = state.get("max_retries_per_competitor", 2)
    needing_retry = competitors_needing_research_retry(
        state.get("research_results", []), state.get("retry_counts", {}), max_retries
    )
    if not needing_retry:
        return None
    by_id = {c["id"]: c for c in state.get("competitors", [])}
    return [
        Send("web_research_node", {**state, "_target_competitor": by_id[cid]})
        for cid in needing_retry
        if cid in by_id
    ]


def edge_partial_failure(state: ResearchGraphState) -> Literal["fail_run", "proceed"]:
    successful = successful_competitor_ids(state.get("research_results", []))
    return "proceed" if successful else "fail_run"


def edge_fan_out_analysis(state: ResearchGraphState) -> list[Send]:
    successful_ids = set(successful_competitor_ids(state.get("research_results", [])))
    by_id = {c["id"]: c for c in state.get("competitors", [])}
    return [
        Send("analysis_node", {**state, "_target_competitor": by_id[cid]})
        for cid in successful_ids
        if cid in by_id
    ]


def route_after_research_join(state: ResearchGraphState) -> list[Send] | Literal["fail_run"]:
    retry_sends = edge_research_retry(state)
    if retry_sends:
        return retry_sends
    if edge_partial_failure(state) == "fail_run":
        return "fail_run"
    return edge_fan_out_analysis(state)


def edge_coverage_check(state: ResearchGraphState) -> list[Send] | Literal["compile_briefing"]:
    coverage_threshold = state.get("coverage_threshold", 0.6)
    max_gap_retries = state.get("max_gap_retries", 1)
    needing_gap = competitors_needing_gap_research(
        state.get("analysis_results", []),
        coverage_threshold,
        state.get("gap_retry_counts", {}),
        max_gap_retries,
    )
    if not needing_gap:
        return "compile_briefing"
    by_id = {c["id"]: c for c in state.get("competitors", [])}
    return [
        Send("gap_research_node", {**state, "_target_competitor": by_id[cid]})
        for cid in needing_gap
        if cid in by_id
    ]
