"""Correct-abstention accuracy for missing-information scenarios (MR-034..040).
The 0-2 rubric score per scenario comes from an abstention judge prompt
(reuses judges/faithfulness_judge.py's JudgeVerdict shape rather than a
bespoke model — see eval/README.md); this module only aggregates."""

_MAX_SCORE = 2


def abstention_accuracy(scores: list[int]) -> float:
    """Fraction of scenarios scored the maximum (2 = explicit, correct
    abstention). A hedge (1) or a fabrication (0) both count as incorrect —
    partial credit is deliberately not given, since a hedge that implies an
    unsupported conclusion is exactly the failure mode this metric exists
    to catch."""
    if not scores:
        return 1.0
    correct = sum(1 for s in scores if s >= _MAX_SCORE)
    return round(correct / len(scores), 4)
