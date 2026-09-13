"""Covers the remaining deterministic/aggregation evaluators not exercised by
test_retrieval_metrics.py / test_cost_accuracy.py / test_release_gate.py."""

from eval.evaluators.abstention import abstention_accuracy
from eval.evaluators.conflict_resolution import (
    aggregate_conflict_resolution,
    normalize_conflict_score,
)
from eval.evaluators.faithfulness import aggregate_faithfulness
from eval.evaluators.freshness import aggregate_freshness, normalize_freshness_score
from eval.evaluators.latency import latency_stats
from eval.evaluators.partial_failure import (
    no_fabricated_facts_for_failed_branch,
    partial_failure_correctness,
)
from eval.evaluators.quality_score import compute_quality_score
from eval.evaluators.unsupported_claims import unsupported_claim_rate
from eval.schemas.eval_models import QualityJudgeVerdict


def test_normalize_conflict_score_scale():
    assert normalize_conflict_score(4) == 1.0
    assert normalize_conflict_score(0) == 0.0
    assert normalize_conflict_score(3) == 0.75


def test_aggregate_conflict_resolution_no_conflicts_is_vacuous_one():
    assert aggregate_conflict_resolution([]) == 1.0


def test_aggregate_conflict_resolution_meets_target():
    scores = [4, 4, 3, 4]  # normalized: 1, 1, .75, 1 -> avg .9375
    assert aggregate_conflict_resolution(scores) == 0.9375


def test_aggregate_faithfulness():
    assert aggregate_faithfulness([]) == 1.0
    assert aggregate_faithfulness([4, 2]) == 0.75


def test_abstention_accuracy_only_full_marks_count():
    assert abstention_accuracy([2, 2, 1, 0]) == 0.5
    assert abstention_accuracy([]) == 1.0


def test_freshness_normalization_and_aggregate():
    assert normalize_freshness_score(3) == 1.0
    assert normalize_freshness_score(0) == 0.0
    expected = round((normalize_freshness_score(3) + normalize_freshness_score(1)) / 2, 4)
    assert aggregate_freshness([3, 1]) == expected


def test_latency_stats_empty_samples():
    stats = latency_stats([])
    assert stats["count"] == 0
    assert stats["p95"] == 0.0


def test_latency_stats_single_sample():
    stats = latency_stats([12.5])
    assert stats["p95"] == 12.5
    assert stats["mean"] == 12.5


def test_latency_stats_p95_over_repeated_runs():
    samples = [float(x) for x in range(1, 101)]  # 1..100
    stats = latency_stats(samples)
    assert stats["p95"] == 95.05
    assert stats["min"] == 1.0
    assert stats["max"] == 100.0


def test_unsupported_claim_rate_zero_total_claims():
    assert unsupported_claim_rate(0, 0) == 0.0


def test_unsupported_claim_rate_normal():
    assert unsupported_claim_rate(20, 1) == 0.05


def test_partial_failure_correctness_no_expected_failures_is_true():
    assert partial_failure_correctness(set(), []) is True


def test_partial_failure_correctness_detects_unmarked_failure():
    results = [{"competitor_id": "c1", "failed": False}, {"competitor_id": "c2", "failed": False}]
    assert partial_failure_correctness({"c1"}, results) is False


def test_partial_failure_correctness_true_when_marked_and_others_succeed():
    results = [{"competitor_id": "c1", "failed": True}, {"competitor_id": "c2", "failed": False}]
    assert partial_failure_correctness({"c1"}, results) is True


def test_no_fabricated_facts_missing_profile_is_fine():
    assert no_fabricated_facts_for_failed_branch(None) is True


def test_no_fabricated_facts_detects_confident_claim_on_failed_branch():
    profile = {"pricing": [{"value": "$99/mo", "is_unsupported": False}]}
    assert no_fabricated_facts_for_failed_branch(profile) is False


def test_compute_quality_score_excludes_cost_and_latency_by_construction():
    verdict = QualityJudgeVerdict(
        factual_correctness=4,
        evidence_faithfulness=4,
        coverage=4,
        conflict_handling=4,
        red_flag_handling=4,
        reason="all good",
    )
    assert compute_quality_score(verdict) == 1.0
