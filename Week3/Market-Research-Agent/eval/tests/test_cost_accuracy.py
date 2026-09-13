from eval.evaluators.cost_accuracy import (
    cost_accuracy,
    cost_breakdown_errors,
    cost_error,
    cost_gate_status,
)


def test_cost_error_normal_case():
    assert cost_error(projected=1.10, actual=1.00) == 0.10
    assert cost_accuracy(projected=1.10, actual=1.00) == 0.90


def test_cost_error_zero_actual_and_zero_projected_is_zero_error():
    assert cost_error(projected=0.0, actual=0.0) == 0.0


def test_cost_error_zero_actual_nonzero_projected_is_max_error():
    assert cost_error(projected=5.0, actual=0.0) == 1.0


def test_cost_gate_thresholds():
    assert cost_gate_status(0.05) == "PASS"
    assert cost_gate_status(0.10) == "PASS"
    assert cost_gate_status(0.15) == "WARNING"
    assert cost_gate_status(0.20) == "WARNING"
    assert cost_gate_status(0.25) == "FAIL"


def test_cost_breakdown_errors_missing_provider_treated_as_zero():
    projected = {"llm": 1.0, "embeddings": 0.5}
    actual = {"llm": 1.0, "search": 0.2}
    errors = cost_breakdown_errors(projected, actual)
    assert errors["llm"] == 0.0
    assert errors["embeddings"] == 1.0  # projected>0, actual missing (0)
    assert errors["search"] == 1.0  # actual>0, projected missing (0)
