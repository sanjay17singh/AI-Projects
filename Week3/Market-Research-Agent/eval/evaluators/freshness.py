"""Temporal/freshness correctness for MR-056..058. 0-3 rubric score per
scenario comes from a freshness judge prompt; this module normalizes/aggregates."""


def normalize_freshness_score(score: int) -> float:
    return round(score / 3, 4)


def aggregate_freshness(scores: list[int]) -> float:
    if not scores:
        return 1.0
    normalized = [normalize_freshness_score(s) for s in scores]
    return round(sum(normalized) / len(normalized), 4)
