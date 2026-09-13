from typing import Any

from app.prompts.injection_guard import SYSTEM_INJECTION_GUARD, wrap_retrieved_content
from app.schemas.common import UNSUPPORTED_VALUE

# One fixed retrieval query per category — used both as the Pinecone query
# text (embedded then matched against stored chunks) and, implicitly, as the
# lens the Analysis Agent retrieves through category-by-category.
RETRIEVAL_QUERY_TEMPLATES: dict[str, str] = {
    "company_description": "What does {competitor} do? Company overview.",
    "pricing": "What is {competitor}'s pricing and plans?",
    "core_features": "What are {competitor}'s core product features?",
    "target_customers": "Who are {competitor}'s target customers?",
    "positioning": "How does {competitor} position itself in the market?",
    "differentiators": "What differentiates {competitor} from its competitors?",
    "announcements": (
        "What recent product announcements, partnerships, or acquisitions has {competitor} made?"
    ),
    "recent_news": "What recent news has been published about {competitor}?",
    "free_trial": "Does {competitor} offer a free plan or a free trial? What are the terms?",
    "customer_reviews": "What do customer reviews say about {competitor}?",
    "notable_customers": "Who are {competitor}'s notable customers or published case studies?",
}


def build_retrieval_query(competitor_name: str, category: str) -> str:
    return RETRIEVAL_QUERY_TEMPLATES[category].format(competitor=competitor_name)


EXTRACTION_SYSTEM_PROMPT = (
    "You are a competitive-intelligence analyst extracting a structured competitor profile "
    "from retrieved evidence. Rules:\n"
    "1. Every claim value must cite the evidence_id(s) it came from in `evidence_ids`. Never "
    "state a fact without at least one evidence_id.\n"
    f"2. If a category has no supporting evidence, set its value to exactly "
    f"'{UNSUPPORTED_VALUE}' and leave evidence_ids empty.\n"
    "3. Set `is_inference=true` for anything you deduced rather than read directly (e.g. "
    "inferring company size from job-posting count); leave it false for direct statements.\n"
    "4. If two pieces of evidence disagree on the same fact (e.g. two different funding "
    "amounts), do not pick one — return both as separate entries in the same category and "
    "give them the same `conflicting_group_id` string, each with its own evidence_ids and "
    "source_dates. Then judge whether the conflict is resolvable from the evidence itself "
    "(e.g. one source is clearly more recent, or one is official/authoritative and the other "
    "is a third-party review or forum post): if so, set `is_preferred=true` on the value you "
    "judge current/authoritative, `resolution_status='resolved'` on every entry in the group, "
    "and a short `resolution_reason` (also repeated on every entry in the group) explaining "
    "why. If you cannot confidently prefer one value, set `resolution_status='unresolved'` on "
    "every entry in the group and leave `is_preferred=false` and `resolution_reason=null`. Use "
    "`resolution_status='human_review_required'` instead of 'unresolved' when the conflict is "
    "high-stakes (e.g. pricing, acquisition status) and evidence is roughly equally credible "
    "on both sides. Never silently drop the losing value.\n"
    "5. Assign confidence 'high' only when backed by 2+ independent sources; 'medium' for a "
    "single credible source or an official source; 'low' for weak/indirect evidence.\n"
    "6. Separately, identify red flags: material negative developments about the competitor "
    "that a buyer or analyst should know about — e.g. a significant price increase, product "
    "discontinuation, a security or data-breach incident, major layoffs or restructuring, a "
    "regulatory or legal issue, a pattern of customer complaints or churn, a deprecated "
    "feature, or an acquisition that creates product-continuity uncertainty. Only report a "
    "red flag if the evidence directly supports it — never infer one from silence or absence "
    "of evidence. Every red flag must cite at least one evidence_id. Set `severity` to "
    "'critical' only for issues that would materially change a buy/build/partner decision "
    "(e.g. an active security breach, a discontinuation, or an unresolved legal action); use "
    "'high'/'medium'/'low' for lesser concerns. If there is no evidence of any red flag, "
    "return an empty list for `red_flags` — do not invent one to appear thorough.\n\n"
    f"{SYSTEM_INJECTION_GUARD}"
)


def build_extraction_messages(
    competitor_name: str, evidence_by_category: dict[str, list[dict[str, Any]]]
) -> list[tuple[str, str]]:
    blocks = []
    for category, items in evidence_by_category.items():
        if not items:
            blocks.append(f"## {category}\n(no evidence retrieved)")
            continue
        rendered = "\n\n".join(
            wrap_retrieved_content(
                source=f"evidence_id={item['evidence_id']} url={item['url']}",
                text=item["text"],
            )
            for item in items
        )
        blocks.append(f"## {category}\n{rendered}")

    human = (
        f"Competitor: {competitor_name}\n\n"
        "Extract a CompetitorProfile from the evidence below, grouped by category. Use the "
        "evidence_id shown in each block's `source` attribute when citing.\n\n"
        + "\n\n".join(blocks)
    )
    return [("system", EXTRACTION_SYSTEM_PROMPT), ("human", human)]
