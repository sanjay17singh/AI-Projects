"""Deterministic Recall@K — exact-ID matching against the Golden Dataset's
`relevant_evidence_ids`."""


def recall_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    """Relevant retrieved evidence found in top K / total relevant expected.

    No relevant evidence expected (`relevant_ids` empty) is treated as a
    vacuous 1.0 (nothing to miss) rather than a divide-by-zero — callers
    that need to distinguish "no expectation" from "perfect recall" should
    check `len(relevant_ids) == 0` themselves before aggregating.
    """
    if not relevant_ids:
        return 1.0
    if k <= 0:
        return 0.0
    top_k = set(retrieved_ids[:k])
    found = len(top_k & relevant_ids)
    return round(found / len(relevant_ids), 4)


def recall_at_k_batch(
    scenarios: list[tuple[list[str], set[str], int]],
) -> dict[str, float]:
    if not scenarios:
        return {"mean": 0.0, "count": 0}
    values = [recall_at_k(r, rel, k) for r, rel, k in scenarios]
    return {"mean": round(sum(values) / len(values), 4), "count": len(values)}
