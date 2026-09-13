"""Latency percentile reporting. p95/p99 in particular are only meaningful
across repeated executions (see eval/README.md's repetitions guidance —
60x1 for dev, 60x3 for release-candidate, 60x5 for major release); a single
run's "p95" is just its max and should not be reported as such."""

import math


def _percentile(sorted_values: list[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    k = (len(sorted_values) - 1) * pct
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_values[int(k)]
    return sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f)


def latency_stats(samples: list[float]) -> dict[str, float]:
    if not samples:
        return {
            "mean": 0.0,
            "median": 0.0,
            "p50": 0.0,
            "p90": 0.0,
            "p95": 0.0,
            "p99": 0.0,
            "min": 0.0,
            "max": 0.0,
            "count": 0,
        }
    s = sorted(samples)
    return {
        "mean": round(sum(s) / len(s), 4),
        "median": round(_percentile(s, 0.5), 4),
        "p50": round(_percentile(s, 0.5), 4),
        "p90": round(_percentile(s, 0.9), 4),
        "p95": round(_percentile(s, 0.95), 4),
        "p99": round(_percentile(s, 0.99), 4),
        "min": round(s[0], 4),
        "max": round(s[-1], 4),
        "count": len(s),
    }
