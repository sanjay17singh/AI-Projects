from pydantic import BaseModel, Field

# Categories fetched by the Web Research Agent. Note: 11 fetched categories
# (this list's 10 + NEWS_CATEGORY below) vs. the 10 COVERAGE_CATEGORIES in
# schemas/common.py — company_description is fetched as context/evidence but
# doesn't count toward evidence_coverage_score.
RESEARCH_CATEGORIES = [
    "company_description",
    "pricing",
    "core_features",
    "target_customers",
    "positioning",
    "differentiators",
    "announcements",
    "free_trial",
    "customer_reviews",
    "notable_customers",
]
NEWS_CATEGORY = "news"


def storage_category_for(profile_field: str) -> str:
    """CompetitorProfile field names mostly match stored evidence categories
    1:1, except recent_news (profile field) <-> news (stored category)."""
    return NEWS_CATEGORY if profile_field == "recent_news" else profile_field


class RawSearchResult(BaseModel):
    """One result as returned by a search client, before dedup/chunking."""

    title: str | None = None
    url: str
    snippet: str | None = None
    highlights: list[str] | None = None
    published_at: str | None = None
    category: str
    query_used: str
    source_type: str = "web"  # "web" | "news"
    provider: str = "you_com"  # "you_com" | "serper"


class WebResearchResult(BaseModel):
    competitor_id: str
    evidence_ids: list[str] = Field(default_factory=list)
    categories_covered: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)
    failed: bool = False


class GapRequest(BaseModel):
    competitor_id: str
    missing_categories: list[str]
