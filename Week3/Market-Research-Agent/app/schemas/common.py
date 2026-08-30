from enum import StrEnum

UNSUPPORTED_VALUE = "Not publicly available"

# The 10 CompetitorProfile categories that count toward evidence_coverage_score.
# company_description is fetched as evidence/context but is not one of the 10 —
# see the coverage formula in services/analysis_service.py.
COVERAGE_CATEGORIES = [
    "pricing",
    "core_features",
    "target_customers",
    "positioning",
    "differentiators",
    "announcements",
    "recent_news",
    "free_trial",
    "customer_reviews",
    "notable_customers",
]

# All categories a CompetitorProfile carries, including company_description
# which is retrieved/populated but excluded from the coverage-score formula.
ALL_PROFILE_CATEGORIES = ["company_description", *COVERAGE_CATEGORIES]


class Classification(StrEnum):
    DIRECT = "direct"
    INDIRECT = "indirect"
    EMERGING = "emerging"


class Confidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RunStatus(StrEnum):
    DISCOVERY_PENDING = "discovery_pending"
    DISCOVERY_COMPLETE = "discovery_complete"
    DISCOVERY_FAILED = "discovery_failed"
    AWAITING_SELECTION = "awaiting_selection"
    RESEARCH_RUNNING = "research_running"
    AWAITING_BUDGET_APPROVAL = "awaiting_budget_approval"
    ANALYSIS_RUNNING = "analysis_running"
    COMPILING = "compiling"
    COMPLETE = "complete"
    FAILED = "failed"


NEWS_WINDOW_CHOICES = (30, 60, 90, 180, 365)
