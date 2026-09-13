import pytest
from pydantic import ValidationError

from eval.schemas.eval_models import (
    GoldenScenario,
    ScenarioInputs,
    ScenarioMetadata,
    ScenarioReferenceOutputs,
)


def _minimal_scenario(**overrides) -> dict:
    base = {
        "inputs": ScenarioInputs(
            scenario_id="MR-001",
            target_company="Acme",
            competitors=["Rival Co"],
            question="What is Rival Co's pricing?",
            research_category="pricing",
        ),
        "reference_outputs": ScenarioReferenceOutputs(),
        "metadata": ScenarioMetadata(case_type="PASS", primary_metric="retrieval_precision"),
    }
    base.update(overrides)
    return base


def test_minimal_golden_scenario_round_trips_through_json():
    scenario = GoldenScenario(**_minimal_scenario())
    dumped = scenario.model_dump_json()
    restored = GoldenScenario.model_validate_json(dumped)
    assert restored.inputs.scenario_id == "MR-001"


def test_invalid_case_type_is_rejected():
    with pytest.raises(ValidationError):
        ScenarioMetadata(case_type="NOT_A_CASE_TYPE", primary_metric="x")


def test_invalid_severity_is_rejected():
    from eval.schemas.eval_models import GoldRedFlag

    with pytest.raises(ValidationError):
        GoldRedFlag(
            red_flag_id="RF-1",
            type="x",
            description="x",
            severity="catastrophic",  # not in the 4-value Literal
            expected_agent_response="x",
        )


def test_reference_outputs_defaults_are_empty_not_none():
    ref = ScenarioReferenceOutputs()
    assert ref.expected_claims == []
    assert ref.expected_red_flags == []
    assert ref.gold_facts == []
    assert ref.expected_cost_range is None
