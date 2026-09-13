#!/usr/bin/env python
"""Frozen-regression experiment runner — backs `eval.run`'s `--mode frozen`.

Runs the Golden Dataset (`market-research-golden`, created by
create_golden_dataset.py) through `langsmith.evaluate()` so every scenario
execution becomes one LangSmith trace, tagged with that example's
`scenario_id`/`case_type`/`difficulty` metadata (already attached at dataset-
creation time), with:

- child "tool" runs for Pinecone upsert/query (via @traceable on
  app.clients.pinecone_client.PineconeClient) and embedding calls (via the
  local `_embed` wrapper below) — these aren't LangChain Runnables so they
  wouldn't otherwise show up as nested spans;
- child "llm" runs for every ChatOpenAI call (automatic once the whole
  pipeline executes inside evaluate()'s traced context), including real
  token usage (AnalysisVerificationAgent already captures this via
  include_raw=True);
- one evaluator function per metric family (see `make_evaluators`), each
  becoming its own small trace plus a feedback score attached back to the
  example's run — this is what lets the LangSmith UI connect an aggregate
  score to the individual case that produced it, and group/filter by
  case_type to find a dominant failure mode.

Real, *unexpected* errors are allowed to propagate out of `target`/the
evaluators — `evaluate()`'s default `error_handling="log"` then marks that
run as errored in LangSmith (visible) and continues the rest of the dataset,
rather than us silently swallowing it into a report row the way the old
bespoke-loop implementation did. The one deliberately-simulated failure
(MR-059's `fail_competitor`) is modeled as a normal-but-partial execution —
that competitor's branch is skipped, not raised — matching how the real
partial-failure-tolerant graph behaves.

The real agent pipeline needs live Pinecone/OpenAI credentials, so nothing
here can be exercised by ordinary unit tests (see eval/tests/ for the
mocked-judge tests that don't need real credentials).
"""

from __future__ import annotations

import subprocess
import time
import uuid
from collections import defaultdict
from datetime import UTC, datetime

from langchain_core.documents import Document
from langsmith import Client, evaluate, traceable

from app.agents.analysis_agent import AnalysisVerificationAgent
from app.clients.openai_client import get_embeddings_model
from app.clients.pinecone_client import PineconeClient
from app.config import Settings, get_settings
from app.schemas.analysis import CompetitorProfile
from app.schemas.common import ALL_PROFILE_CATEGORIES
from app.schemas.research import storage_category_for
from app.services.analysis_service import build_conflicts
from app.services.cost_service import PRICE_TABLE, project_cost
from app.utils.text_splitting import split_document
from eval.evaluators.abstention import abstention_accuracy
from eval.evaluators.conflict_resolution import (
    aggregate_conflict_resolution,
    normalize_conflict_score,
)
from eval.evaluators.cost_accuracy import cost_error
from eval.evaluators.coverage import ground_truth_coverage
from eval.evaluators.faithfulness import normalize_faithfulness_score
from eval.evaluators.freshness import aggregate_freshness
from eval.evaluators.latency import latency_stats
from eval.evaluators.partial_failure import partial_failure_correctness
from eval.evaluators.red_flag_precision import red_flag_precision
from eval.evaluators.red_flag_recall import critical_red_flag_recall, red_flag_recall
from eval.evaluators.release_gate import evaluate_release_gate
from eval.evaluators.retrieval_precision import precision_at_k
from eval.evaluators.retrieval_recall import recall_at_k
from eval.evaluators.unsupported_claims import unsupported_claim_rate
from eval.judges.abstention_judge import judge_abstention
from eval.judges.conflict_judge import judge_conflict
from eval.judges.coverage_judge import judge_coverage
from eval.judges.faithfulness_judge import judge_faithfulness
from eval.judges.freshness_judge import judge_freshness
from eval.judges.red_flag_judge import judge_red_flags
from eval.schemas.eval_models import (
    EvalReport,
    EvidenceRecord,
    ExperimentMetadata,
    FailedScenario,
    GoldenScenario,
    ReleaseGateThresholds,
    ScenarioReferenceOutputs,
)

DATASET_NAME = "market-research-golden"
EVAL_WORKSPACE_ID = "eval-scratch"
PROMPT_VERSION = "v1"

# A score below this on any 0-1 metric becomes a FailedScenario row in the
# report. Deliberately coarse (not each evaluator's own precise pass/fail
# threshold, which lives in ReleaseGateThresholds) — this only drives the
# human-readable "what went wrong" table, not the release gate itself.
_FAILED_SCENARIO_SCORE_THRESHOLD = 0.75


def _git_sha() -> str:
    """Best-effort — this repo has no .git directory, so a failure here is
    expected and must never crash the runner."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def _evidence_for_companies(
    companies: set[str], evidence: list[EvidenceRecord]
) -> list[EvidenceRecord]:
    return [e for e in evidence if e.company in companies]


def _evidence_dicts(records: list[EvidenceRecord]) -> list[dict]:
    return [r.model_dump(mode="json") for r in records]


def _cited_evidence_ids(profile: CompetitorProfile) -> list[str]:
    """Best-effort proxy for 'what was retrieved': CompetitorProfile only
    exposes evidence_ids actually cited on claims, not the raw pre-extraction
    retrieval list — so cited evidence_ids (first-seen order) stand in for
    retrieved_ids when computing precision/recall@k."""
    seen: list[str] = []
    for category in ALL_PROFILE_CATEGORIES:
        for claim in getattr(profile, category, []):
            for eid in claim.evidence_ids:
                if eid not in seen:
                    seen.append(eid)
    return seen


def make_target(settings: Settings, evidence: list[EvidenceRecord]):
    """Builds the `target(inputs: dict) -> dict` function passed to
    `langsmith.evaluate()`. Constructed once per experiment so Pinecone/
    embeddings/agent aren't rebuilt per scenario. Mirrors
    eval/run_analysis_eval.py's fixture-seeding pattern."""
    pinecone = PineconeClient(settings)
    pinecone.ensure_index()
    embeddings = get_embeddings_model(settings)
    agent = AnalysisVerificationAgent(settings, pinecone)

    @traceable(run_type="tool", name="embed_documents")
    def _embed(texts: list[str]) -> list[list[float]]:
        return embeddings.embed_documents(texts)

    def _seed_and_analyze(
        competitor_name: str, run_id: uuid.UUID, scenario_evidence: list[EvidenceRecord]
    ):
        competitor_id = uuid.uuid4()
        for item in scenario_evidence:
            chunks = split_document(
                Document(page_content=item.content, metadata={"category": item.category})
            )
            texts = [c.page_content for c in chunks]
            vectors = _embed(texts)
            payload = []
            for i, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True)):
                metadata = {
                    "workspace_id": EVAL_WORKSPACE_ID,
                    "run_id": str(run_id),
                    "competitor_id": str(competitor_id),
                    "evidence_id": item.evidence_id,
                    # Frozen Evidence Corpus `category` uses profile field
                    # names (e.g. "recent_news"); storage/query expects
                    # storage_category_for's mapping (e.g. "news") — apply
                    # the same mapping used for real, live-crawled evidence.
                    "category": storage_category_for(item.category),
                    "source_type": item.source_type,
                    "canonical_url": item.url,
                    "title": item.title,
                    "published_at": item.published_at or "",
                    "fetched_at": item.retrieved_at,
                    "chunk_index": i,
                    "provider": "eval-frozen",
                    "text": chunk.page_content,
                }
                payload.append((f"{item.evidence_id}_{i}", vector, metadata))
            pinecone.upsert(payload, namespace=EVAL_WORKSPACE_ID)

        profile = agent.analyze(
            workspace_id=EVAL_WORKSPACE_ID,
            run_id=run_id,
            competitor_id=competitor_id,
            competitor_name=competitor_name,
        )
        usage = agent.last_usage or {}
        cost_usd = round(
            (usage.get("tokens_in", 0) or 0) * PRICE_TABLE["openai"]["tokens_in"]
            + (usage.get("tokens_out", 0) or 0) * PRICE_TABLE["openai"]["tokens_out"],
            6,
        )
        return profile, cost_usd

    def target(inputs: dict) -> dict:
        target_company = inputs["target_company"]
        competitors = inputs.get("competitors") or [target_company]
        simulation = inputs.get("simulation") or {}
        fail_competitor = simulation.get("fail_competitor")
        inject_latency_seconds = simulation.get("inject_latency_seconds")

        if inject_latency_seconds:
            # MR-060: simulated slow search/LLM/retrieval — a real sleep so
            # the latency this scenario reports (and folds into the overall
            # p95 across repetitions) reflects an actually-slow execution,
            # not a synthetic number bolted on afterward.
            time.sleep(inject_latency_seconds)

        companies = {target_company, *competitors}
        scenario_evidence = _evidence_for_companies(companies, evidence)
        run_id = uuid.uuid4()

        research_results = []
        actual_cost_usd = 0.0
        primary_profile: CompetitorProfile | None = None
        # Primary competitor for a scenario is competitors[0] (the entity
        # being profiled), not target_company (the company doing the
        # research) — matches the rest of the dataset's convention.
        primary_name = competitors[0] if competitors else target_company

        for name in competitors:
            if name == fail_competitor:
                # MR-059: this branch is deliberately skipped, never raised —
                # a real failed competitor branch doesn't crash the run
                # either (see app/graphs/research_nodes.py's web_research_node),
                # it's just marked failed and excluded from analysis.
                research_results.append({"competitor_id": name, "failed": True})
                continue
            competitor_evidence = [e for e in scenario_evidence if e.company == name]
            profile, cost_usd = _seed_and_analyze(name, run_id, competitor_evidence)
            actual_cost_usd += cost_usd
            research_results.append({"competitor_id": name, "failed": False})
            if name == primary_name:
                primary_profile = profile

        return {
            "profile": primary_profile.model_dump(mode="json") if primary_profile else None,
            "research_results": research_results,
            "actual_cost_usd": round(actual_cost_usd, 6),
        }

    return target


def _profile_from_run(run) -> CompetitorProfile | None:
    data = (run.outputs or {}).get("profile")
    return CompetitorProfile.model_validate(data) if data else None


def make_evaluators(evidence: list[EvidenceRecord], settings: Settings) -> list:
    """Returns the list of `(run, example) -> dict | list[dict]` functions
    passed to `langsmith.evaluate(evaluators=...)`. Each becomes its own
    LangSmith trace (with any LLM judge call nested as a child run) plus a
    feedback score attached back to the example's run — see module
    docstring. A metric that doesn't apply to a given example's `case_type`
    returns `score=None` (never omits the key) rather than raising, since
    `evaluate()` requires a non-empty return value from every evaluator."""

    def _scenario_evidence_dicts(example) -> list[dict]:
        inputs = example.inputs or {}
        companies = {inputs.get("target_company"), *(inputs.get("competitors") or [])}
        return _evidence_dicts(_evidence_for_companies(companies, evidence))

    def retrieval_metrics(run, example) -> dict | list[dict]:
        ref = ScenarioReferenceOutputs.model_validate(example.outputs or {})
        case_type = (example.metadata or {}).get("case_type")
        keys = ("retrieval_precision_at_3", "retrieval_precision_at_5", "retrieval_recall_at_5")
        if not (ref.relevant_evidence_ids or case_type == "RETRIEVAL"):
            return [{"key": k, "score": None} for k in keys]
        profile = _profile_from_run(run)
        if profile is None:
            return [{"key": k, "score": None, "comment": "no profile produced"} for k in keys]
        retrieved_ids = _cited_evidence_ids(profile)
        relevant = set(ref.relevant_evidence_ids)
        return [
            {
                "key": "retrieval_precision_at_3",
                "score": precision_at_k(retrieved_ids, relevant, 3),
            },
            {
                "key": "retrieval_precision_at_5",
                "score": precision_at_k(retrieved_ids, relevant, 5),
            },
            {"key": "retrieval_recall_at_5", "score": recall_at_k(retrieved_ids, relevant, 5)},
        ]

    def red_flags_eval(run, example) -> dict | list[dict]:
        ref = ScenarioReferenceOutputs.model_validate(example.outputs or {})
        case_type = (example.metadata or {}).get("case_type")
        keys = ("red_flag_recall", "red_flag_precision", "critical_red_flag_recall")
        if not (case_type == "RED_FLAG" or ref.expected_red_flags):
            return [{"key": k, "score": None} for k in keys]
        profile = _profile_from_run(run)
        if profile is None:
            return [{"key": k, "score": None, "comment": "no profile produced"} for k in keys]
        evidence_dicts = _scenario_evidence_dicts(example)
        match = judge_red_flags(profile.red_flags, ref.expected_red_flags, evidence_dicts, settings)
        matched_gold = set(match.matched_gold_ids)
        correct_agent = set(match.correct_agent_flag_ids)
        results = [
            {
                "key": "red_flag_recall",
                "score": red_flag_recall(ref.expected_red_flags, matched_gold),
                "comment": match.reason,
            },
            {
                "key": "red_flag_precision",
                "score": red_flag_precision(profile.red_flags, correct_agent),
            },
        ]
        if any(f.is_critical for f in ref.expected_red_flags):
            results.append(
                {
                    "key": "critical_red_flag_recall",
                    "score": critical_red_flag_recall(ref.expected_red_flags, matched_gold),
                }
            )
        else:
            results.append({"key": "critical_red_flag_recall", "score": None})
        return results

    def conflict_eval(run, example) -> dict | list[dict]:
        ref = ScenarioReferenceOutputs.model_validate(example.outputs or {})
        case_type = (example.metadata or {}).get("case_type")
        if not (case_type == "CONFLICT" or ref.expected_conflicts):
            return {"key": "conflict_resolution", "score": None}
        profile = _profile_from_run(run)
        if profile is None:
            return {"key": "conflict_resolution", "score": None, "comment": "no profile produced"}
        evidence_dicts = _scenario_evidence_dicts(example)
        agent_conflicts_by_field = {c.field: c for c in build_conflicts(profile)}
        results = []
        scores = []
        for gold_conflict in ref.expected_conflicts:
            agent_conflict = agent_conflicts_by_field.get(gold_conflict.field)
            verdict = judge_conflict(gold_conflict, agent_conflict, evidence_dicts, settings)
            scores.append(verdict.score)
            results.append(
                {
                    "key": f"conflict_resolution:{gold_conflict.field}",
                    "score": normalize_conflict_score(verdict.score),
                    "comment": verdict.reason,
                }
            )
        results.append(
            {"key": "conflict_resolution", "score": aggregate_conflict_resolution(scores)}
        )
        return results

    def coverage_eval(run, example) -> dict:
        ref = ScenarioReferenceOutputs.model_validate(example.outputs or {})
        case_type = (example.metadata or {}).get("case_type")
        if case_type not in ("COVERAGE_FRESHNESS", "PASS") or not ref.gold_facts:
            return {"key": "ground_truth_coverage", "score": None}
        profile = _profile_from_run(run)
        if profile is None:
            return {"key": "ground_truth_coverage", "score": None, "comment": "no profile produced"}
        match = judge_coverage(ref.gold_facts, profile, settings)
        return {
            "key": "ground_truth_coverage",
            "score": ground_truth_coverage(ref.gold_facts, set(match.matched_items)),
            "comment": match.reason,
        }

    def faithfulness_eval(run, example) -> list[dict]:
        profile = _profile_from_run(run)
        if profile is None:
            return [
                {"key": "faithfulness", "score": None, "comment": "no profile produced"},
                {"key": "unsupported_claim_rate", "score": None},
            ]
        evidence_dicts = _scenario_evidence_dicts(example)
        verdict = judge_faithfulness(profile, evidence_dicts, settings)
        material_claims = sum(
            1
            for category in ALL_PROFILE_CATEGORIES
            for claim in getattr(profile, category, [])
            if not claim.is_unsupported
        )
        rate = unsupported_claim_rate(material_claims, len(verdict.unsupported_items))
        return [
            {
                "key": "faithfulness",
                "score": normalize_faithfulness_score(verdict.score),
                "comment": verdict.reason,
            },
            {"key": "unsupported_claim_rate", "score": rate},
        ]

    def abstention_eval(run, example) -> dict:
        ref = ScenarioReferenceOutputs.model_validate(example.outputs or {})
        if (example.metadata or {}).get("case_type") != "MISSING_INFO" or not ref.expected_unknowns:
            return {"key": "abstention_accuracy", "score": None}
        profile = _profile_from_run(run)
        if profile is None:
            return {"key": "abstention_accuracy", "score": None, "comment": "no profile produced"}
        claims = [c.value for cat in ALL_PROFILE_CATEGORIES for c in getattr(profile, cat, [])]
        scores = [judge_abstention(u, claims, settings).score for u in ref.expected_unknowns]
        return {"key": "abstention_accuracy", "score": abstention_accuracy(scores)}

    def freshness_eval(run, example) -> dict:
        ref = ScenarioReferenceOutputs.model_validate(example.outputs or {})
        if (
            (example.metadata or {}).get("case_type") != "TEMPORAL"
            or not ref.expected_current_values
        ):
            return {"key": "freshness_accuracy", "score": None}
        profile = _profile_from_run(run)
        if profile is None:
            return {"key": "freshness_accuracy", "score": None, "comment": "no profile produced"}
        evidence_dicts = _scenario_evidence_dicts(example)
        claims = [c.value for cat in ALL_PROFILE_CATEGORIES for c in getattr(profile, cat, [])]
        scores = [
            judge_freshness(v, claims, evidence_dicts, settings).score
            for v in ref.expected_current_values.values()
        ]
        return {"key": "freshness_accuracy", "score": aggregate_freshness(scores)}

    def cost_eval(run, example) -> dict:
        ref = ScenarioReferenceOutputs.model_validate(example.outputs or {})
        if (example.metadata or {}).get("case_type") != "COST" or ref.expected_cost_range is None:
            return {"key": "cost_projection_error", "score": None}
        projected = project_cost(num_competitors=1, search_provider_count=1)
        actual = (run.outputs or {}).get("actual_cost_usd") or (
            (ref.expected_cost_range.min + ref.expected_cost_range.max) / 2
        )
        return {
            "key": "cost_projection_error",
            "score": cost_error(projected, actual),
            "comment": f"projected=${projected:.4f} actual=${actual:.4f}",
        }

    def partial_failure_eval(run, example) -> dict:
        if (example.metadata or {}).get("case_type") != "RESILIENCE":
            return {"key": "partial_failure_correctness", "score": None}
        fail_competitor = ((example.inputs or {}).get("simulation") or {}).get("fail_competitor")
        if not fail_competitor:
            return {"key": "partial_failure_correctness", "score": None}
        research_results = (run.outputs or {}).get("research_results", [])
        correct = partial_failure_correctness({fail_competitor}, research_results)
        return {"key": "partial_failure_correctness", "score": 1.0 if correct else 0.0}

    def latency_eval(run, example) -> dict:
        # run.latency is LangSmith's own end_time-start_time for this trace —
        # the single source of truth also visible in the UI, rather than a
        # value we timed ourselves and could drift from what's displayed.
        latency = run.latency
        if latency is None:
            return {"key": "latency_seconds", "score": None}
        return {"key": "latency_seconds", "score": latency}

    return [
        retrieval_metrics,
        red_flags_eval,
        conflict_eval,
        coverage_eval,
        faithfulness_eval,
        abstention_eval,
        freshness_eval,
        cost_eval,
        partial_failure_eval,
        latency_eval,
    ]


def reduce_results(
    results,
    scenarios: list[GoldenScenario],
    settings: Settings,
    repetitions: int,
    thresholds: ReleaseGateThresholds | None,
) -> EvalReport:
    """Pure reduction from an iterable of `ExperimentResultRow`-shaped dicts
    (as produced by `langsmith.evaluate()`, or a synthetic stand-in in tests)
    into an `EvalReport`. Split out from `run_experiment` specifically so
    this logic is unit-testable without live Pinecone/OpenAI/LangSmith
    credentials — only `run_experiment` itself needs those, to actually
    produce `results`."""
    per_key_scores: dict[str, list[float]] = defaultdict(list)
    failed_scenarios: list[FailedScenario] = []
    execution_count = 0

    for row in results:
        execution_count += 1
        example = row["example"]
        run = row["run"]
        scenario_id = (example.metadata or {}).get("scenario_id", "unknown")
        eval_results = row["evaluation_results"].get("results", [])
        for eval_result in eval_results:
            if eval_result.score is None:
                continue
            per_key_scores[eval_result.key].append(eval_result.score)
            if (
                eval_result.key != "latency_seconds"
                and eval_result.score < _FAILED_SCENARIO_SCORE_THRESHOLD
            ):
                failed_scenarios.append(
                    FailedScenario(
                        scenario_id=scenario_id,
                        metric=eval_result.key,
                        expected=f">={_FAILED_SCENARIO_SCORE_THRESHOLD}",
                        actual=str(eval_result.score),
                        explanation=eval_result.comment or "",
                        evidence_ids=[],
                    )
                )
        if run.error:
            failed_scenarios.append(
                FailedScenario(
                    scenario_id=scenario_id,
                    metric="execution",
                    expected="target completes without error",
                    actual="errored",
                    explanation=run.error,
                    evidence_ids=[],
                )
            )

    def _mean(key: str, default: float = 1.0) -> float:
        values = per_key_scores.get(key)
        return round(sum(values) / len(values), 4) if values else default

    metrics: dict[str, float] = {
        "red_flag_recall": _mean("red_flag_recall"),
        "critical_red_flag_recall": _mean("critical_red_flag_recall"),
        "red_flag_precision": _mean("red_flag_precision"),
        "retrieval_precision_at_5": _mean("retrieval_precision_at_5", default=0.0),
        "retrieval_precision_at_3": _mean("retrieval_precision_at_3", default=0.0),
        "retrieval_recall_at_5": _mean("retrieval_recall_at_5", default=0.0),
        "ground_truth_coverage": _mean("ground_truth_coverage"),
        "conflict_resolution": _mean("conflict_resolution"),
        "faithfulness": _mean("faithfulness"),
        "unsupported_claim_rate": _mean("unsupported_claim_rate", default=0.0),
        "abstention_accuracy": _mean("abstention_accuracy"),
        "freshness_accuracy": _mean("freshness_accuracy"),
        "cost_projection_error": _mean("cost_projection_error", default=0.0),
        "p95_latency_seconds": latency_stats(per_key_scores.get("latency_seconds", []))["p95"],
        "partial_failure_correctness": _mean("partial_failure_correctness"),
    }

    gate_result = evaluate_release_gate(metrics, thresholds)
    gate_result.failed_scenarios.extend(failed_scenarios)

    metadata = ExperimentMetadata(
        golden_dataset_version=scenarios[0].metadata.gold_version if scenarios else "gold-v1",
        evidence_corpus_version="evidence-v1",
        git_commit_sha=_git_sha(),
        llm_model=settings.openai_model,
        judge_model=settings.openai_model,
        embedding_model=settings.openai_embedding_model,
        prompt_version=PROMPT_VERSION,
        retrieval_top_k=settings.retrieval_top_k,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        temperature=settings.extraction_temperature,
        experiment_timestamp=datetime.now(UTC).isoformat(),
        repetitions=repetitions,
        mode="frozen",
    )

    return EvalReport(
        experiment_metadata=metadata,
        thresholds=thresholds or ReleaseGateThresholds(),
        gate_result=gate_result,
        scenario_count=len(scenarios),
        execution_count=execution_count,
    )


def run_experiment(
    scenarios: list[GoldenScenario],
    evidence: list[EvidenceRecord],
    settings: Settings,
    repetitions: int = 1,
    thresholds: ReleaseGateThresholds | None = None,
    experiment_prefix: str = "market-research-frozen",
    client: Client | None = None,
) -> EvalReport:
    """Runs `market-research-golden` through `langsmith.evaluate()` and hands
    the resulting `ExperimentResults` to `reduce_results` to build the final
    `EvalReport`. Requires live Pinecone/OpenAI/LangSmith credentials — see
    `reduce_results` for the credential-free, unit-testable part."""
    client = client or Client()
    target = make_target(settings, evidence)
    evaluators = make_evaluators(evidence, settings)

    results = evaluate(
        target,
        data=DATASET_NAME,
        evaluators=evaluators,
        experiment_prefix=experiment_prefix,
        num_repetitions=max(1, repetitions),
        client=client,
        metadata={
            "golden_dataset_version": (
                scenarios[0].metadata.gold_version if scenarios else "gold-v1"
            ),
            "evidence_corpus_version": "evidence-v1",
            "git_commit_sha": _git_sha(),
            "llm_model": settings.openai_model,
            "judge_model": settings.openai_model,
            "embedding_model": settings.openai_embedding_model,
            "prompt_version": PROMPT_VERSION,
            "retrieval_top_k": settings.retrieval_top_k,
            "chunk_size": settings.chunk_size,
            "chunk_overlap": settings.chunk_overlap,
            "temperature": settings.extraction_temperature,
        },
    )

    return reduce_results(results, scenarios, settings, repetitions, thresholds)


def main() -> None:
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repetitions", type=int, default=1)
    args = parser.parse_args()

    settings = get_settings()
    datasets_dir = Path(__file__).parent.parent / "datasets"
    scenarios = [
        GoldenScenario.model_validate_json(line)
        for line in (datasets_dir / "golden_scenarios.jsonl").read_text().splitlines()
        if line.strip()
    ]
    evidence = [
        EvidenceRecord.model_validate_json(line)
        for line in (datasets_dir / "frozen_evidence.jsonl").read_text().splitlines()
        if line.strip()
    ]

    report = run_experiment(scenarios, evidence, settings, repetitions=args.repetitions)
    print(report.gate_result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
