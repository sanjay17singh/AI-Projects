"""Evidence faithfulness. The 0-4 rubric score per profile/claim-set comes
from judges/faithfulness_judge.py (semantic, frozen-evidence-only); this
module normalizes and aggregates."""


def normalize_faithfulness_score(score: int) -> float:
    return round(score / 4, 4)


def aggregate_faithfulness(scores: list[int]) -> float:
    if not scores:
        return 1.0
    normalized = [normalize_faithfulness_score(s) for s in scores]
    return round(sum(normalized) / len(normalized), 4)
