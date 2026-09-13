"""Release-gate evaluation. Pure Python — given a dict of already-computed
metric values (from the other evaluators/judges) and a ReleaseGateThresholds,
decide PASS/WARNING/FAIL. The one hard rule that overrides everything else:
critical_red_flag_recall < 1.00 is always a hard FAIL, regardless of every
other metric."""

from eval.schemas.eval_models import MetricResult, ReleaseGateResult, ReleaseGateThresholds

# (metric_key, higher_is_better, required_attr, preferred_attr)
_METRIC_SPECS: list[tuple[str, bool, str, str | None]] = [
    ("critical_red_flag_recall", True, "critical_red_flag_recall", None),
    ("red_flag_recall", True, "red_flag_recall", "preferred_red_flag_recall"),
    (
        "retrieval_precision_at_5",
        True,
        "retrieval_precision_at_5",
        "preferred_retrieval_precision_at_5",
    ),
    ("retrieval_recall_at_5", True, "retrieval_recall_at_5", "preferred_retrieval_recall_at_5"),
    ("ground_truth_coverage", True, "ground_truth_coverage", "preferred_ground_truth_coverage"),
    ("conflict_resolution", True, "conflict_resolution", "preferred_conflict_resolution"),
    ("faithfulness", True, "faithfulness", "preferred_faithfulness"),
    ("unsupported_claim_rate", False, "unsupported_claim_rate", "preferred_unsupported_claim_rate"),
    ("cost_projection_error", False, "cost_projection_error", "preferred_cost_projection_error"),
    ("p95_latency_seconds", False, "p95_latency_seconds", "preferred_p95_latency_seconds"),
    ("partial_failure_correctness", True, "partial_failure_correctness", None),
]


def evaluate_release_gate(
    metrics: dict[str, float], thresholds: ReleaseGateThresholds | None = None
) -> ReleaseGateResult:
    thresholds = thresholds or ReleaseGateThresholds()
    results: dict[str, MetricResult] = {}
    failed: list[str] = []
    warnings: list[str] = []

    for key, higher_is_better, required_attr, preferred_attr in _METRIC_SPECS:
        if key not in metrics:
            continue
        value = metrics[key]
        required = getattr(thresholds, required_attr)
        preferred = getattr(thresholds, preferred_attr) if preferred_attr else None

        meets_required = value >= required if higher_is_better else value <= required
        meets_preferred = (
            (value >= preferred if higher_is_better else value <= preferred)
            if preferred is not None
            else meets_required
        )

        if not meets_required:
            status = "FAIL"
            failed.append(key)
        elif not meets_preferred:
            status = "WARNING"
            warnings.append(key)
        else:
            status = "PASS"

        results[key] = MetricResult(
            name=key,
            value=value,
            required_threshold=required,
            preferred_threshold=preferred,
            higher_is_better=higher_is_better,
            passed=(status != "FAIL"),
        )

    hard_fail = metrics.get("critical_red_flag_recall", 1.0) < thresholds.critical_red_flag_recall

    if hard_fail:
        overall = "FAIL"
    elif failed:
        overall = "FAIL"
    elif warnings:
        overall = "WARNING"
    else:
        overall = "PASS"

    return ReleaseGateResult(
        status=overall,
        hard_fail=hard_fail,
        failed_metrics=failed,
        warning_metrics=warnings,
        metrics=results,
    )
