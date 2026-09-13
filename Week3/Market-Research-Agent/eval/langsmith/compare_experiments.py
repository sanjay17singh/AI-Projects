#!/usr/bin/env python
"""Compares two experiment metric sets (baseline vs candidate) and prints a
per-metric delta table, flagging regressions. Reuses
`eval.evaluators.release_gate._METRIC_SPECS` for the higher-is-better flag
per metric rather than redefining it — so "did it get better or worse"
always matches what the release gate itself considers better.

Can be driven from two LangSmith experiment names (fetched via the
LangSmith client and reduced to a metrics dict) or from two plain
`dict[str, float]` metric sets (e.g. two `ReleaseGateResult.metrics`
loaded from disk) — see `compare_experiment_names` vs `compare_metrics`.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass

from eval.evaluators.release_gate import _METRIC_SPECS

_HIGHER_IS_BETTER: dict[str, bool] = {key: higher for key, higher, *_ in _METRIC_SPECS}


@dataclass
class MetricDelta:
    metric: str
    baseline: float
    candidate: float
    delta: float
    higher_is_better: bool
    regression: bool


def compare_metrics(
    baseline: dict[str, float], candidate: dict[str, float]
) -> list[MetricDelta]:
    """Regression = candidate is worse than baseline on a metric present in
    both sets, accounting for higher-is-better vs lower-is-better. A metric
    missing from either side is skipped (nothing to compare)."""
    deltas = []
    for metric in sorted(set(baseline) & set(candidate)):
        base_value = baseline[metric]
        cand_value = candidate[metric]
        higher_is_better = _HIGHER_IS_BETTER.get(metric, True)
        delta = round(cand_value - base_value, 4)
        regression = (delta < 0) if higher_is_better else (delta > 0)
        deltas.append(
            MetricDelta(
                metric=metric,
                baseline=base_value,
                candidate=cand_value,
                delta=delta,
                higher_is_better=higher_is_better,
                regression=regression,
            )
        )
    return deltas


def format_delta_table(deltas: list[MetricDelta]) -> str:
    header = f"{'Metric':<32} {'Baseline':>10} {'Candidate':>10} {'Delta':>10}  Regression"
    lines = [header, "-" * len(header)]
    for d in deltas:
        flag = "REGRESSION" if d.regression else ""
        lines.append(
            f"{d.metric:<32} {d.baseline:>10.4f} {d.candidate:>10.4f} {d.delta:>+10.4f}  {flag}"
        )
    regressions = [d.metric for d in deltas if d.regression]
    lines.append("")
    lines.append(
        f"{len(regressions)} regression(s): {', '.join(regressions)}"
        if regressions
        else "No regressions."
    )
    return "\n".join(lines)


def compare_experiment_names(baseline_name: str, candidate_name: str) -> list[MetricDelta]:
    """Fetches two named LangSmith experiments' feedback-derived mean scores
    and compares them. Requires a real LANGCHAIN_API_KEY; not exercised in
    unit tests (see eval/tests/test_compare_experiments.py, which tests
    compare_metrics directly against synthetic dicts)."""
    from langsmith import Client

    client = Client()

    def _metrics_for(experiment_name: str) -> dict[str, float]:
        runs = list(client.list_runs(project_name=experiment_name, is_root=True))
        totals: dict[str, list[float]] = {}
        for run in runs:
            for feedback in client.list_feedback(run_ids=[run.id]):
                if feedback.score is not None:
                    totals.setdefault(feedback.key, []).append(feedback.score)
        return {key: round(sum(v) / len(v), 4) for key, v in totals.items()}

    baseline = _metrics_for(baseline_name)
    candidate = _metrics_for(candidate_name)
    return compare_metrics(baseline, candidate)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-json", help="Path to a JSON file of {metric: value}")
    parser.add_argument("--candidate-json", help="Path to a JSON file of {metric: value}")
    parser.add_argument("--baseline-experiment", help="LangSmith experiment name")
    parser.add_argument("--candidate-experiment", help="LangSmith experiment name")
    args = parser.parse_args()

    if args.baseline_json and args.candidate_json:
        with open(args.baseline_json) as f:
            baseline = json.load(f)
        with open(args.candidate_json) as f:
            candidate = json.load(f)
        deltas = compare_metrics(baseline, candidate)
    elif args.baseline_experiment and args.candidate_experiment:
        deltas = compare_experiment_names(args.baseline_experiment, args.candidate_experiment)
    else:
        parser.error(
            "Pass either --baseline-json/--candidate-json or "
            "--baseline-experiment/--candidate-experiment"
        )
        return

    print(format_delta_table(deltas))


if __name__ == "__main__":
    main()
