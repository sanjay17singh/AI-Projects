from eval.langsmith.compare_experiments import compare_metrics, format_delta_table


def test_compare_metrics_flags_regression_on_higher_is_better_metric():
    baseline = {"red_flag_recall": 0.95, "faithfulness": 0.92}
    candidate = {"red_flag_recall": 0.88, "faithfulness": 0.94}

    deltas = compare_metrics(baseline, candidate)
    by_metric = {d.metric: d for d in deltas}

    assert by_metric["red_flag_recall"].regression is True
    assert by_metric["red_flag_recall"].delta < 0
    assert by_metric["faithfulness"].regression is False
    assert by_metric["faithfulness"].delta > 0


def test_compare_metrics_flags_regression_on_lower_is_better_metric():
    baseline = {"unsupported_claim_rate": 0.02, "p95_latency_seconds": 30.0}
    candidate = {"unsupported_claim_rate": 0.05, "p95_latency_seconds": 25.0}

    deltas = compare_metrics(baseline, candidate)
    by_metric = {d.metric: d for d in deltas}

    assert by_metric["unsupported_claim_rate"].regression is True
    assert by_metric["p95_latency_seconds"].regression is False


def test_compare_metrics_skips_metrics_missing_from_either_side():
    baseline = {"red_flag_recall": 0.95, "only_in_baseline": 1.0}
    candidate = {"red_flag_recall": 0.95, "only_in_candidate": 1.0}

    deltas = compare_metrics(baseline, candidate)

    assert [d.metric for d in deltas] == ["red_flag_recall"]


def test_format_delta_table_reports_regression_count():
    baseline = {"red_flag_recall": 0.95}
    candidate = {"red_flag_recall": 0.80}

    deltas = compare_metrics(baseline, candidate)
    table = format_delta_table(deltas)

    assert "REGRESSION" in table
    assert "1 regression(s): red_flag_recall" in table


def test_format_delta_table_reports_no_regressions():
    baseline = {"red_flag_recall": 0.95}
    candidate = {"red_flag_recall": 0.97}

    deltas = compare_metrics(baseline, candidate)
    table = format_delta_table(deltas)

    assert "No regressions." in table
