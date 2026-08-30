"""Pure-Python helpers used by graphs/edges.py's conditional-edge functions.
Deliberately free of LangGraph imports and LLM calls so the routing logic
they back is trivially unit-testable and obviously deterministic.

Note on state shape: research_results / analysis_results are
Annotated[list, operator.add] in ResearchGraphState, so a retried competitor
gets a SECOND entry appended rather than its first entry replaced. Every
helper here works off latest_by_key() so "does competitor X currently need a
retry" always reflects its most recent attempt, not a stale earlier one.
"""

from typing import Any


def latest_by_key(items: list[dict[str, Any]], key: str = "competitor_id") -> dict[str, dict]:
    latest: dict[str, dict] = {}
    for item in items:
        latest[item[key]] = item
    return latest


def is_over_budget(
    projected_cost_usd: float, actual_cost_usd: float, budget_usd_limit: float
) -> bool:
    return max(projected_cost_usd, actual_cost_usd) > budget_usd_limit


def competitors_needing_research_retry(
    research_results: list[dict[str, Any]], retry_counts: dict[str, int], max_retries: int
) -> list[str]:
    latest = latest_by_key(research_results)
    return [
        cid
        for cid, result in latest.items()
        if result.get("failed") and retry_counts.get(cid, 0) < max_retries
    ]


def successful_competitor_ids(research_results: list[dict[str, Any]]) -> list[str]:
    latest = latest_by_key(research_results)
    return [cid for cid, result in latest.items() if not result.get("failed")]


def competitors_needing_gap_research(
    analysis_results: list[dict[str, Any]],
    coverage_threshold: float,
    gap_retry_counts: dict[str, int],
    max_gap_retries: int,
) -> list[str]:
    latest = latest_by_key(analysis_results)
    return [
        cid
        for cid, result in latest.items()
        if result.get("evidence_coverage_score", 0) < coverage_threshold
        and gap_retry_counts.get(cid, 0) < max_gap_retries
    ]
