import operator
from typing import Annotated, Any, TypedDict


class DiscoveryGraphState(TypedDict, total=False):
    run_id: str
    workspace_id: str
    target_company_name: str
    target_company_website: str | None
    industry: str | None
    geography: str | None
    customer_segment: str | None
    news_window_days: int

    normalized_request: dict[str, Any] | None
    search_queries: list[str]
    raw_search_results: list[dict[str, Any]]
    candidates: list[dict[str, Any]]

    retry_count: int
    max_retries: int
    errors: list[str]
    status: str


class ResearchGraphState(TypedDict, total=False):
    run_id: str
    workspace_id: str
    competitors: list[dict[str, Any]]  # [{id, name, website, classification}, ...]
    news_window_days: int

    budget_usd_limit: float
    projected_cost_usd: float
    actual_cost_usd: float
    approved: bool

    # Annotated with operator.add so concurrent Send branches merge without
    # clobbering each other's results.
    research_results: Annotated[list[dict[str, Any]], operator.add]
    analysis_results: Annotated[list[dict[str, Any]], operator.add]

    retry_counts: dict[str, int]
    max_retries_per_competitor: int
    gap_retry_counts: dict[str, int]
    max_gap_retries: int
    coverage_threshold: float

    status: str
