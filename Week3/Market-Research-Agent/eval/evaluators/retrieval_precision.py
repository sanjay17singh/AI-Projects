"""Deterministic Precision@K — exact-ID matching against the Golden
Dataset's `relevant_evidence_ids`, no LLM judgment needed or wanted."""


def precision_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    """Relevant retrieved evidence in the top K / K.

    K larger than the retrieved set still divides by K (not by the smaller
    retrieved count) — a shallow retrieval that only returns 2 of a
    requested 5 should be penalized, not rewarded with an inflated ratio.
    Empty `retrieved_ids` or k<=0 yields 0.0 rather than raising.
    """
    if k <= 0:
        return 0.0
    top_k = retrieved_ids[:k]
    if not top_k:
        return 0.0
    relevant_count = sum(1 for eid in top_k if eid in relevant_ids)
    return round(relevant_count / k, 4)


def precision_at_k_batch(
    scenarios: list[tuple[list[str], set[str], int]],
) -> dict[str, float]:
    """Aggregate mean Precision@K across scenarios; each tuple is
    (retrieved_ids, relevant_ids, k). Returns {"mean": ..., "count": n}."""
    if not scenarios:
        return {"mean": 0.0, "count": 0}
    values = [precision_at_k(r, rel, k) for r, rel, k in scenarios]
    return {"mean": round(sum(values) / len(values), 4), "count": len(values)}
