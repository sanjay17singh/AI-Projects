from eval.evaluators.release_gate import evaluate_release_gate
from eval.schemas.eval_models import ReleaseGateThresholds

_ALL_PASS_METRICS = {
    "critical_red_flag_recall": 1.00,
    "red_flag_recall": 0.96,
    "retrieval_precision_at_5": 0.82,
    "retrieval_recall_at_5": 0.91,
    "ground_truth_coverage": 0.92,
    "conflict_resolution": 0.96,
    "faithfulness": 0.96,
    "unsupported_claim_rate": 0.018,
    "cost_projection_error": 0.074,
    "p95_latency_seconds": 40.0,
    "partial_failure_correctness": 1.00,
}


def test_all_metrics_clearing_preferred_targets_is_pass():
    result = evaluate_release_gate(_ALL_PASS_METRICS)
    assert result.status == "PASS"
    assert result.failed_metrics == []
    assert result.warning_metrics == []


def test_metric_between_required_and_preferred_is_warning():
    # clears 0.90 required, misses 0.95 preferred
    metrics = dict(_ALL_PASS_METRICS, red_flag_recall=0.91)
    result = evaluate_release_gate(metrics)
    assert result.status == "WARNING"
    assert "red_flag_recall" in result.warning_metrics


def test_metric_below_required_is_fail():
    metrics = dict(_ALL_PASS_METRICS, retrieval_precision_at_5=0.65)  # below 0.70 required
    result = evaluate_release_gate(metrics)
    assert result.status == "FAIL"
    assert "retrieval_precision_at_5" in result.failed_metrics


def test_critical_red_flag_recall_below_one_is_always_hard_fail():
    metrics = dict(_ALL_PASS_METRICS, critical_red_flag_recall=0.99)
    result = evaluate_release_gate(metrics)
    assert result.status == "FAIL"
    assert result.hard_fail is True


def test_custom_thresholds_are_respected():
    thresholds = ReleaseGateThresholds(
        retrieval_precision_at_5=0.50, preferred_retrieval_precision_at_5=0.50
    )
    metrics = dict(_ALL_PASS_METRICS, retrieval_precision_at_5=0.55)
    result = evaluate_release_gate(metrics, thresholds)
    assert result.status == "PASS"


def test_missing_metric_is_simply_absent_not_a_crash():
    result = evaluate_release_gate({"critical_red_flag_recall": 1.0})
    assert "red_flag_recall" not in result.metrics
