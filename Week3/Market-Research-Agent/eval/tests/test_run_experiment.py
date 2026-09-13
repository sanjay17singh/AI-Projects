"""Unit tests for the credential-free parts of eval/langsmith/run_experiment.py:
`reduce_results` (pure reduction over synthetic ExperimentResultRow-shaped
dicts) and the individual evaluator functions from `make_evaluators` (LLM
judges mocked via tests.fixtures.fake_llm.FakeChatModel, matching
eval/tests/test_judges_structural.py's pattern). `run_experiment`/`make_target`
themselves need live Pinecone/OpenAI/LangSmith credentials and are not
exercised here."""

from dataclasses import dataclass, field
from types import SimpleNamespace
from unittest.mock import patch

from app.schemas.analysis import ClaimField, CompetitorProfile, RedFlag
from eval.evaluators.release_gate import ReleaseGateThresholds
from eval.langsmith.run_experiment import make_evaluators, reduce_results
from eval.schemas.eval_models import GoldenScenario
from tests.fixtures.fake_llm import FakeChatModel


@dataclass
class FakeEvalResult:
    key: str
    score: float | None
    comment: str | None = None


@dataclass
class FakeExample:
    inputs: dict = field(default_factory=dict)
    outputs: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)


@dataclass
class FakeRun:
    outputs: dict | None = None
    latency: float | None = None
    error: str | None = None


def _scenario(**overrides) -> GoldenScenario:
    base = {
        "inputs": {
            "scenario_id": "MR-001",
            "target_company": "Pipeline Harbor",
            "competitors": ["Northwind Analytics"],
            "question": "What is Northwind Analytics' pricing?",
            "research_category": "pricing",
            "top_k": 5,
        },
        "reference_outputs": {},
        "metadata": {
            "case_type": "PASS",
            "primary_metric": "faithfulness",
            "gold_version": "gold-v1",
        },
    }
    base.update(overrides)
    return GoldenScenario.model_validate(base)


def _row(scenario_id: str, results: list[FakeEvalResult], error: str | None = None) -> dict:
    return {
        "run": FakeRun(latency=1.23, error=error),
        "example": FakeExample(metadata={"scenario_id": scenario_id, "case_type": "PASS"}),
        "evaluation_results": {"results": results},
    }


def test_reduce_results_aggregates_scores_into_metrics():
    rows = [
        _row(
            "MR-001",
            [FakeEvalResult("faithfulness", 1.0), FakeEvalResult("ground_truth_coverage", 0.9)],
        ),
        _row(
            "MR-002",
            [FakeEvalResult("faithfulness", 0.5), FakeEvalResult("ground_truth_coverage", 0.7)],
        ),
    ]
    report = reduce_results(rows, [_scenario()], settings=SimpleNamespace(
        openai_model="gpt-4o-mini", openai_embedding_model="text-embedding-3-small",
        retrieval_top_k=6, chunk_size=1000, chunk_overlap=150, extraction_temperature=0.0,
    ), repetitions=1, thresholds=None)

    assert report.gate_result.metrics["faithfulness"].value == 0.75
    assert report.gate_result.metrics["ground_truth_coverage"].value == 0.8
    assert report.execution_count == 2


def test_reduce_results_skips_none_scores():
    rows = [
        _row("MR-001", [FakeEvalResult("faithfulness", None), FakeEvalResult("faithfulness", 1.0)])
    ]
    report = reduce_results(rows, [_scenario()], settings=SimpleNamespace(
        openai_model="x", openai_embedding_model="x", retrieval_top_k=6, chunk_size=1000,
        chunk_overlap=150, extraction_temperature=0.0,
    ), repetitions=1, thresholds=None)
    assert report.gate_result.metrics["faithfulness"].value == 1.0


def test_reduce_results_flags_low_scores_as_failed_scenarios():
    rows = [_row("MR-003", [FakeEvalResult("faithfulness", 0.2, comment="hallucinated a claim")])]
    report = reduce_results(rows, [_scenario()], settings=SimpleNamespace(
        openai_model="x", openai_embedding_model="x", retrieval_top_k=6, chunk_size=1000,
        chunk_overlap=150, extraction_temperature=0.0,
    ), repetitions=1, thresholds=None)
    failed = report.gate_result.failed_scenarios
    assert len(failed) == 1
    assert failed[0].scenario_id == "MR-003"
    assert failed[0].metric == "faithfulness"
    assert failed[0].explanation == "hallucinated a claim"


def test_reduce_results_surfaces_run_errors_as_failed_scenarios():
    rows = [_row("MR-004", [], error="OpenAI API timeout")]
    report = reduce_results(rows, [_scenario()], settings=SimpleNamespace(
        openai_model="x", openai_embedding_model="x", retrieval_top_k=6, chunk_size=1000,
        chunk_overlap=150, extraction_temperature=0.0,
    ), repetitions=1, thresholds=None)
    failed = report.gate_result.failed_scenarios
    assert any(f.metric == "execution" and f.explanation == "OpenAI API timeout" for f in failed)


def test_reduce_results_latency_is_not_flagged_as_failed_regardless_of_value():
    rows = [_row("MR-005", [FakeEvalResult("latency_seconds", 90.0)])]
    report = reduce_results(rows, [_scenario()], settings=SimpleNamespace(
        openai_model="x", openai_embedding_model="x", retrieval_top_k=6, chunk_size=1000,
        chunk_overlap=150, extraction_temperature=0.0,
    ), repetitions=1, thresholds=None)
    assert report.gate_result.failed_scenarios == []
    assert report.gate_result.metrics["p95_latency_seconds"].value == 90.0


def test_reduce_results_empty_input_still_produces_a_report():
    report = reduce_results([], [_scenario()], settings=SimpleNamespace(
        openai_model="x", openai_embedding_model="x", retrieval_top_k=6, chunk_size=1000,
        chunk_overlap=150, extraction_temperature=0.0,
    ), repetitions=1, thresholds=ReleaseGateThresholds())
    assert report.execution_count == 0
    assert report.gate_result.metrics["critical_red_flag_recall"].value == 1.0


def test_retrieval_evaluator_scores_precision_and_recall():
    settings = SimpleNamespace(openai_model="x")
    evaluators = make_evaluators(evidence=[], settings=settings)
    retrieval_metrics = evaluators[0]

    example = FakeExample(
        inputs={"target_company": "Pipeline Harbor", "competitors": ["Northwind Analytics"]},
        outputs={"relevant_evidence_ids": ["EV-1", "EV-2"]},
        metadata={"case_type": "RETRIEVAL"},
    )
    profile = CompetitorProfile(
        competitor_id="c1",
        competitor_name="Northwind Analytics",
        pricing=[ClaimField(value="$79/mo", evidence_ids=["EV-1"])],
    )
    run = FakeRun(outputs={"profile": profile.model_dump(mode="json")})

    results = retrieval_metrics(run, example)
    scores = {r["key"]: r["score"] for r in results}
    assert scores["retrieval_recall_at_5"] == 0.5
    assert scores["retrieval_precision_at_5"] == 0.2


def test_retrieval_evaluator_returns_none_scores_when_not_applicable():
    settings = SimpleNamespace(openai_model="x")
    retrieval_metrics = make_evaluators(evidence=[], settings=settings)[0]
    example = FakeExample(inputs={}, outputs={}, metadata={"case_type": "PASS"})
    run = FakeRun(outputs=None)
    results = retrieval_metrics(run, example)
    assert all(r["score"] is None for r in results)


def test_red_flags_evaluator_uses_judge_and_scores_recall_precision():
    from eval.judges.red_flag_judge import RedFlagMatchResult

    fake_result = RedFlagMatchResult(
        matched_gold_ids=["RF-1"], correct_agent_flag_ids=["agent-1"], reason="matched"
    )
    fake_model = FakeChatModel({RedFlagMatchResult: fake_result})

    settings = SimpleNamespace(openai_model="x")
    red_flags_eval = make_evaluators(evidence=[], settings=settings)[1]

    example = FakeExample(
        inputs={"target_company": "Pipeline Harbor", "competitors": ["Harborlight Cloud"]},
        outputs={
            "expected_red_flags": [
                {
                    "red_flag_id": "RF-1",
                    "type": "price_increase",
                    "description": "raised prices",
                    "severity": "critical",
                    "is_critical": True,
                }
            ]
        },
        metadata={"case_type": "RED_FLAG"},
    )
    profile = CompetitorProfile(
        competitor_id="c1",
        competitor_name="Harborlight Cloud",
        red_flags=[
            RedFlag(
                red_flag_id="agent-1",
                type="price_increase",
                severity="critical",
                description="raised prices 50%",
                evidence_ids=["EV-1"],
            )
        ],
    )
    run = FakeRun(outputs={"profile": profile.model_dump(mode="json")})

    with patch("eval.judges.red_flag_judge.get_chat_model", return_value=fake_model):
        results = red_flags_eval(run, example)

    scores = {r["key"]: r["score"] for r in results}
    assert scores["red_flag_recall"] == 1.0
    assert scores["red_flag_precision"] == 1.0
    assert scores["critical_red_flag_recall"] == 1.0
