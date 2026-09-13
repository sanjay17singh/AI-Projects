"""Projected-vs-actual cost accuracy. Plain arithmetic — actual cost comes
from app.db.models.RunCost rows (see app/services/cost_service.py), projected
cost from app.services.cost_service.project_cost(); both are already real
numbers by the time they reach this module."""

from typing import Literal

GateStatus = Literal["PASS", "WARNING", "FAIL"]


def cost_error(projected: float, actual: float) -> float:
    """abs(projected - actual) / actual. actual == 0 is a degenerate case
    (e.g. a mocked/zero-cost run): returns 0.0 if projected is also 0
    (perfect agreement), else 1.0 (maximal error) rather than raising."""
    if actual == 0:
        return 0.0 if projected == 0 else 1.0
    return round(abs(projected - actual) / actual, 4)


def cost_accuracy(projected: float, actual: float) -> float:
    return round(1 - cost_error(projected, actual), 4)


def cost_gate_status(error: float) -> GateStatus:
    if error <= 0.10:
        return "PASS"
    if error <= 0.20:
        return "WARNING"
    return "FAIL"


def cost_breakdown_errors(
    projected_by_provider: dict[str, float], actual_by_provider: dict[str, float]
) -> dict[str, float]:
    """Per-provider cost error, e.g. {"llm": .., "search": .., "embeddings": .., "total": ..}.
    A provider present in one dict but not the other is treated as 0.0 for
    the missing side (not skipped) so a completely-missing cost category is
    still visible as error rather than silently absent from the report."""
    providers = set(projected_by_provider) | set(actual_by_provider)
    return {
        provider: cost_error(
            projected_by_provider.get(provider, 0.0), actual_by_provider.get(provider, 0.0)
        )
        for provider in providers
    }
