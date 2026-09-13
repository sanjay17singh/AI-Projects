from eval.evaluators.release_gate import evaluate_release_gate
from eval.reports.generate_report import generate_report
from eval.schemas.eval_models import (
    EvalReport,
    ExperimentMetadata,
    FailedScenario,
    ReleaseGateThresholds,
)

_METADATA = ExperimentMetadata(
    golden_dataset_version="gold-v1",
    evidence_corpus_version="evidence-v1",
    git_commit_sha="",
    llm_model="gpt-4o-mini",
    judge_model="gpt-4o-mini",
    embedding_model="text-embedding-3-small",
    prompt_version="v1",
    retrieval_top_k=5,
    chunk_size=1000,
    chunk_overlap=150,
    temperature=0.0,
    experiment_timestamp="2026-09-12T00:00:00+00:00",
    repetitions=1,
    mode="frozen",
)

_ALL_PASS_METRICS = {
    "critical_red_flag_recall": 1.00,
    "red_flag_recall": 0.96,
    "red_flag_precision": 0.95,
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


def _build_report(metrics: dict[str, float], failed_scenarios=None) -> EvalReport:
    gate_result = evaluate_release_gate(metrics)
    if failed_scenarios:
        gate_result.failed_scenarios.extend(failed_scenarios)
    return EvalReport(
        experiment_metadata=_METADATA,
        thresholds=ReleaseGateThresholds(),
        gate_result=gate_result,
        scenario_count=60,
        execution_count=60,
    )


def test_generate_report_contains_all_section_headers():
    report = _build_report(_ALL_PASS_METRICS)
    text = generate_report(report)

    headers = [
        "QUALITY",
        "RETRIEVAL",
        "OPERATIONS",
        "RESILIENCE",
        "FINAL RELEASE STATUS",
        "Failed Scenarios",
    ]
    for header in headers:
        assert header in text


def test_generate_report_shows_pass_status_when_all_metrics_pass():
    report = _build_report(_ALL_PASS_METRICS)
    text = generate_report(report)

    assert "**PASS**" in text
    assert "(none)" in text


def test_generate_report_shows_fail_status_and_failed_scenario_row():
    metrics = dict(_ALL_PASS_METRICS, critical_red_flag_recall=0.5)
    failed = [
        FailedScenario(
            scenario_id="MR-001",
            metric="critical_red_flag_recall",
            expected="1.0",
            actual="0.5",
            explanation="Missed a critical red flag.",
            evidence_ids=["EV-1"],
        )
    ]
    report = _build_report(metrics, failed_scenarios=failed)
    text = generate_report(report)

    assert "**FAIL**" in text
    assert "MR-001" in text
    assert "critical_red_flag_recall" in text
    assert "Missed a critical red flag." in text


def test_generate_report_shows_warning_status():
    metrics = dict(_ALL_PASS_METRICS, red_flag_recall=0.91)
    report = _build_report(metrics)
    text = generate_report(report)

    assert "**WARNING**" in text
