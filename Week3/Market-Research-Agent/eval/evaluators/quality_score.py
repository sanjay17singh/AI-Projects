"""Optional aggregate Master Quality Judge score — a weighted combination of
five 0-4 dimensions (judges/quality_judge.py). Deliberately excludes cost and
latency: operational performance must stay separate from answer quality (see
eval/README.md's design principles)."""

from eval.schemas.eval_models import QualityJudgeVerdict

_WEIGHTS = {
    "factual_correctness": 0.25,
    "evidence_faithfulness": 0.25,
    "red_flag_handling": 0.20,
    "conflict_handling": 0.15,
    "coverage": 0.15,
}


def compute_quality_score(verdict: QualityJudgeVerdict) -> float:
    normalized = {
        "factual_correctness": verdict.factual_correctness / 4,
        "evidence_faithfulness": verdict.evidence_faithfulness / 4,
        "red_flag_handling": verdict.red_flag_handling / 4,
        "conflict_handling": verdict.conflict_handling / 4,
        "coverage": verdict.coverage / 4,
    }
    score = sum(_WEIGHTS[dim] * value for dim, value in normalized.items())
    return round(score, 4)
