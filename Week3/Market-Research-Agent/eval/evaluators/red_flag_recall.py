"""Red-flag recall metrics. Semantic matching between the agent's `RedFlag`s
and the Golden Dataset's `GoldRedFlag`s is an LLM-as-judge task (wording
differs — see judges/red_flag_judge.py); this module only does the
arithmetic once a match set is known, so it stays deterministic and unit
testable without mocking an LLM."""

from eval.schemas.eval_models import GoldRedFlag


def red_flag_recall(gold_red_flags: list[GoldRedFlag], matched_gold_ids: set[str]) -> float:
    """Correctly identified gold red flags / total expected gold red flags.
    No expected red flags -> vacuous 1.0."""
    if not gold_red_flags:
        return 1.0
    return round(len(matched_gold_ids) / len(gold_red_flags), 4)


def critical_red_flag_recall(
    gold_red_flags: list[GoldRedFlag], matched_gold_ids: set[str]
) -> float:
    """Same formula restricted to `is_critical` gold flags. Must be 1.0 for
    release — see eval/evaluators/release_gate.py's hard-fail rule."""
    critical = [f for f in gold_red_flags if f.is_critical]
    if not critical:
        return 1.0
    matched_critical = sum(1 for f in critical if f.red_flag_id in matched_gold_ids)
    return round(matched_critical / len(critical), 4)
