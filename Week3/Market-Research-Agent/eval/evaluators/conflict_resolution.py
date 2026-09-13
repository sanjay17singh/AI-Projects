"""Conflict-resolution correctness. The 0-4 rubric score per conflict comes
from judges/conflict_judge.py (semantic — did the agent preserve both
values, cite provenance, resolve only when justified, give a correct
reason); this module only normalizes and aggregates those integer scores."""


def normalize_conflict_score(score: int) -> float:
    return round(score / 4, 4)


def aggregate_conflict_resolution(scores: list[int]) -> float:
    """No conflicts in the batch -> vacuous 1.0."""
    if not scores:
        return 1.0
    normalized = [normalize_conflict_score(s) for s in scores]
    return round(sum(normalized) / len(normalized), 4)
