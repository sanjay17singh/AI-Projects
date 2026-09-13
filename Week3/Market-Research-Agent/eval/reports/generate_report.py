"""Renders the eval report's markdown-ish text format (per product spec)
from an `EvalReport`: header, QUALITY/RETRIEVAL/OPERATIONS/RESILIENCE
sections, FINAL RELEASE STATUS, and a failed-scenarios table."""

from __future__ import annotations

from pathlib import Path

from eval.schemas.eval_models import EvalReport, MetricResult

_QUALITY_METRICS = [
    ("red_flag_recall", "Red Flag Recall"),
    ("critical_red_flag_recall", "Critical Red Flag Recall"),
    ("red_flag_precision", "Red Flag Precision"),
    ("ground_truth_coverage", "Ground Truth Coverage"),
    ("conflict_resolution", "Conflict Resolution"),
    ("faithfulness", "Evidence Faithfulness"),
    ("unsupported_claim_rate", "Unsupported Claim Rate"),
    ("abstention_accuracy", "Abstention Accuracy"),
    ("freshness_accuracy", "Freshness Accuracy"),
]

_RETRIEVAL_METRICS = [
    ("retrieval_precision_at_3", "Precision@3"),
    ("retrieval_precision_at_5", "Precision@5"),
    ("retrieval_recall_at_5", "Recall@5"),
]

_RESILIENCE_METRICS = [
    ("partial_failure_correctness", "Partial-Failure Handling"),
]


def _status_for(metric: MetricResult | None) -> str:
    if metric is None:
        return "N/A"
    if metric.passed is False:
        return "FAIL"
    required_ok = metric.passed is not False
    if metric.preferred_threshold is not None:
        meets_preferred = (
            metric.value >= metric.preferred_threshold
            if metric.higher_is_better
            else metric.value <= metric.preferred_threshold
        )
        if required_ok and not meets_preferred:
            return "WARNING"
    return "PASS" if required_ok else "FAIL"


def _fmt(value: float) -> str:
    return f"{value:.4f}"


def _section(title: str) -> str:
    return f"\n## {title}\n"


def _metric_line(metrics: dict[str, MetricResult], key: str, label: str) -> str | None:
    metric = metrics.get(key)
    if metric is None:
        return None
    status = _status_for(metric)
    threshold = (
        f"required>={metric.required_threshold}"
        if metric.higher_is_better
        else f"required<={metric.required_threshold}"
    )
    return f"- {label}: {_fmt(metric.value)} ({threshold}) — {status}"


def generate_report(report: EvalReport) -> str:
    meta = report.experiment_metadata
    gate = report.gate_result
    metrics = gate.metrics

    lines: list[str] = []
    lines.append("# Market Research Agent — Evaluation Report")
    lines.append("")
    lines.append(f"- Golden Dataset version: {meta.golden_dataset_version}")
    lines.append(f"- Evidence Corpus version: {meta.evidence_corpus_version}")
    lines.append(f"- Mode: {meta.mode} (repetitions={meta.repetitions})")
    lines.append(f"- Scenario count: {report.scenario_count}")
    lines.append(f"- Execution count: {report.execution_count}")
    lines.append(f"- Model: {meta.llm_model} / Judge model: {meta.judge_model}")
    lines.append(f"- Embedding model: {meta.embedding_model}")
    lines.append(f"- Git commit: {meta.git_commit_sha or '(none)'}")
    lines.append(f"- Timestamp: {meta.experiment_timestamp}")

    lines.append(_section("QUALITY"))
    for key, label in _QUALITY_METRICS:
        line = _metric_line(metrics, key, label)
        if line:
            lines.append(line)

    lines.append(_section("RETRIEVAL"))
    for key, label in _RETRIEVAL_METRICS:
        line = _metric_line(metrics, key, label)
        if line:
            lines.append(line)

    lines.append(_section("OPERATIONS"))
    cost_metric = metrics.get("cost_projection_error")
    if cost_metric is not None:
        lines.append(
            f"- Cost projection error: {_fmt(cost_metric.value)} — {_status_for(cost_metric)}"
        )
    latency_metric = metrics.get("p95_latency_seconds")
    if latency_metric is not None:
        lines.append(
            f"- p95 latency (seconds): {_fmt(latency_metric.value)} — {_status_for(latency_metric)}"
        )

    lines.append(_section("RESILIENCE"))
    for key, label in _RESILIENCE_METRICS:
        line = _metric_line(metrics, key, label)
        if line:
            lines.append(line)

    lines.append(_section("FINAL RELEASE STATUS"))
    lines.append(f"**{gate.status}**")
    if gate.hard_fail:
        lines.append("Hard fail: critical_red_flag_recall did not meet its required threshold.")
    if gate.failed_metrics:
        lines.append(f"Failed metrics: {', '.join(gate.failed_metrics)}")
    if gate.warning_metrics:
        lines.append(f"Warning metrics: {', '.join(gate.warning_metrics)}")

    lines.append(_section("Failed Scenarios"))
    if not gate.failed_scenarios:
        lines.append("(none)")
    else:
        lines.append("| scenario_id | metric | expected | actual | explanation | evidence_ids |")
        lines.append("|---|---|---|---|---|---|")
        for fs in gate.failed_scenarios:
            evidence_ids = ", ".join(fs.evidence_ids)
            lines.append(
                f"| {fs.scenario_id} | {fs.metric} | {fs.expected} | {fs.actual} | "
                f"{fs.explanation} | {evidence_ids} |"
            )

    return "\n".join(lines) + "\n"


def write_report(report: EvalReport, path: str | Path) -> str:
    text = generate_report(report)
    Path(path).write_text(text)
    return text
