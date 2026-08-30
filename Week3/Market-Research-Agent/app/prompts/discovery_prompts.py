"""Prompt builders for the Discovery Agent. Each returns a list of
(role, content) message tuples ready for `model.invoke(messages)` where model
already has `.with_structured_output(...)` applied."""

from typing import Any


def normalize_request_messages(raw_request: dict[str, Any]) -> list[tuple[str, str]]:
    system = (
        "You normalize a competitor-research request into complete fields. Fill in any "
        "gaps (industry, geography, customer segment) with your best inference from the "
        "company name and website if given, and note each inference you made in "
        "`assumptions`. Never invent a company name — only industry/geography/segment may "
        "be inferred."
    )
    human = (
        f"target_company_name: {raw_request.get('target_company_name')}\n"
        f"target_company_website: {raw_request.get('target_company_website')}\n"
        f"industry: {raw_request.get('industry')}\n"
        f"geography: {raw_request.get('geography')}\n"
        f"customer_segment: {raw_request.get('customer_segment')}\n"
        f"news_window_days: {raw_request.get('news_window_days')}"
    )
    return [("system", system), ("human", human)]


def generate_queries_messages(
    normalized_request: dict[str, Any], previous_error: str | None = None
) -> list[tuple[str, str]]:
    system = (
        "You write 3-5 web search queries to find companies that compete with the given "
        "target company. Cover direct competitors (same product, same customers), indirect "
        "competitors (adjacent product solving the same problem), and emerging players. "
        "Prefer queries a person would actually type, not keyword soup."
    )
    human = (
        f"Target company: {normalized_request.get('target_company_name')}\n"
        f"Industry: {normalized_request.get('industry')}\n"
        f"Geography: {normalized_request.get('geography')}\n"
        f"Customer segment: {normalized_request.get('customer_segment')}"
    )
    if previous_error:
        human += (
            f"\n\nThe previous search attempt failed ({previous_error}). Write different, "
            "broader queries this time."
        )
    return [("system", system), ("human", human)]


def score_candidates_messages(
    normalized_request: dict[str, Any], raw_results: list[dict[str, Any]]
) -> list[tuple[str, str]]:
    system = (
        "You are a competitive-intelligence analyst. From the search results below, "
        "identify exactly 5 companies that plausibly compete with the target company. "
        "For each, resolve their official website if apparent from the results, write a "
        "1-2 sentence explanation grounded in the search results, list the supporting "
        "source URLs, classify as 'direct' (same product and customers), 'indirect' "
        "(adjacent product, overlapping customers), or 'emerging' (limited market presence "
        "but rising visibility), and score 0-1 on overlap of: product, target customers, "
        "geography, business model, and market visibility. Do not fabricate a company that "
        "doesn't appear in the search results."
    )

    def _content(r: dict[str, Any]) -> str:
        highlights = r.get("highlights")
        if highlights:
            return highlights[0]
        return r.get("snippet") or ""

    results_block = "\n".join(
        f"- title: {r.get('title')}\n  url: {r.get('url')}\n  content: {_content(r)}"
        for r in raw_results
    )
    human = (
        f"Target company: {normalized_request.get('target_company_name')}\n"
        f"Industry: {normalized_request.get('industry')}\n"
        f"Geography: {normalized_request.get('geography')}\n"
        f"Customer segment: {normalized_request.get('customer_segment')}\n\n"
        f"Search results:\n{results_block}"
    )
    return [("system", system), ("human", human)]
