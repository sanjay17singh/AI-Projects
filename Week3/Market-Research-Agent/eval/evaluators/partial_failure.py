"""Resilience: a simulated branch failure (MR-059) must not crash the run,
must be explicitly marked failed, and must not produce fabricated facts for
that branch. Structural/deterministic — no LLM judgment needed since
`WebResearchResult.failed` and `ClaimField.is_unsupported` already carry
the signal."""


def partial_failure_correctness(
    failed_competitor_ids: set[str], research_results: list[dict]
) -> bool:
    """True iff every competitor expected to fail is explicitly marked
    failed=True in its WebResearchResult, and the run still produced
    (non-failed) results for at least the remaining competitors when there
    are any. `research_results` is the list of `WebResearchResult.model_dump()`
    dicts accumulated in ResearchGraphState.research_results."""
    if not failed_competitor_ids:
        return True
    by_id = {r.get("competitor_id"): r for r in research_results}
    all_marked_failed = all(by_id.get(cid, {}).get("failed") for cid in failed_competitor_ids)

    remaining = [r for r in research_results if r.get("competitor_id") not in failed_competitor_ids]
    remaining_ok = not remaining or any(not r.get("failed") for r in remaining)

    return bool(all_marked_failed and remaining_ok)


def no_fabricated_facts_for_failed_branch(profile_dict: dict | None) -> bool:
    """A permanently-failed competitor should either have no persisted
    profile at all, or a profile whose claims are all `is_unsupported`
    (never a confidently-asserted, evidence-cited fact for a branch that
    never actually returned evidence)."""
    if profile_dict is None:
        return True
    for category_claims in profile_dict.values():
        if not isinstance(category_claims, list):
            continue
        for claim in category_claims:
            if isinstance(claim, dict) and not claim.get("is_unsupported", False):
                return False
    return True
