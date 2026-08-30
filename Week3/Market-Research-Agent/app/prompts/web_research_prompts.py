"""Category-specific search query templates for the Web Research Agent. These
are plain string templates, not LLM prompts — the Web Research Agent queries
You.com directly per category rather than asking an LLM to invent queries."""

CATEGORY_QUERY_TEMPLATES: dict[str, str] = {
    "company_description": "{company_name} company overview about",
    "pricing": "{company_name} pricing plans cost",
    "core_features": "{company_name} features product capabilities",
    "target_customers": "{company_name} customers who uses ideal customer",
    "positioning": "{company_name} positioning tagline value proposition",
    "differentiators": "{company_name} vs competitors differentiators unique",
    "announcements": "{company_name} announcement launch partnership acquisition",
    "free_trial": "{company_name} free trial free plan",
    "customer_reviews": "{company_name} reviews rating G2 Capterra",
    "notable_customers": "{company_name} customers case study clients",
}

NEWS_QUERY_TEMPLATE = "{company_name} news"


def build_category_query(company_name: str, category: str) -> str:
    template = CATEGORY_QUERY_TEMPLATES[category]
    return template.format(company_name=company_name)


def build_news_query(company_name: str) -> str:
    return NEWS_QUERY_TEMPLATE.format(company_name=company_name)
