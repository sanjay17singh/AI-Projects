"""Pydantic schemas for the 60-scenario Golden Dataset, the Frozen Evidence
Corpus, LLM-judge verdicts, and release-gate reporting.

Deliberately separate from `app/schemas/` — these describe evaluation
*inputs/expectations* (what a scenario asks for and what the "right" answer
looks like), not agent runtime state. Where the agent already has a
first-class model (e.g. `app.schemas.analysis.CompetitorProfile`, `RedFlag`,
`Conflict`), evaluators import and reuse that model directly rather than
redefining it here — see evaluators/*.py.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

CaseType = Literal[
    "PASS",
    "RETRIEVAL",
    "RED_FLAG",
    "MISSING_INFO",
    "CONFLICT",
    "COVERAGE_FRESHNESS",
    "COST",
    "TEMPORAL",
    "RESILIENCE",
]

Severity = Literal["low", "medium", "high", "critical"]
ResolutionStatus = Literal["resolved", "unresolved", "human_review_required"]
SourceType = Literal[
    "official",
    "documentation",
    "regulatory",
    "reputable_news",
    "review",
    "partner",
    "blog",
    "community",
    "low_authority",
]


# --------------------------------------------------------------------------
# Golden Dataset
# --------------------------------------------------------------------------


class GoldRedFlag(BaseModel):
    red_flag_id: str
    type: str
    description: str
    severity: Severity
    expected_evidence_ids: list[str] = Field(default_factory=list)
    is_critical: bool = False
    expected_agent_response: str = ""


class GoldConflict(BaseModel):
    field: str
    value_a: str
    value_b: str
    evidence_ids_a: list[str] = Field(default_factory=list)
    evidence_ids_b: list[str] = Field(default_factory=list)
    source_authority_a: SourceType | None = None
    source_authority_b: SourceType | None = None
    published_at_a: str | None = None
    published_at_b: str | None = None
    expected_preferred_value: str | None = None
    expected_resolution_reason: str | None = None
    must_remain_unresolved: bool = False
    requires_human_review: bool = False


class GoldFact(BaseModel):
    fact_id: str
    category: str
    statement: str
    evidence_ids: list[str] = Field(default_factory=list)


class CostRange(BaseModel):
    min: float
    max: float


class ScenarioInputs(BaseModel):
    scenario_id: str
    target_company: str
    competitors: list[str] = Field(default_factory=list)
    question: str
    research_category: str
    top_k: int = 5
    # Free-form knobs a scenario may need to simulate (used by resilience
    # scenarios MR-059/MR-060) — e.g. {"fail_competitor": "CompetitorX"} or
    # {"inject_latency_seconds": 12}. Left generic rather than adding one
    # bespoke field per scenario family.
    simulation: dict = Field(default_factory=dict)


class ScenarioReferenceOutputs(BaseModel):
    expected_claims: list[str] = Field(default_factory=list)
    expected_red_flags: list[GoldRedFlag] = Field(default_factory=list)
    relevant_evidence_ids: list[str] = Field(default_factory=list)
    required_evidence_ids: list[str] = Field(default_factory=list)
    expected_conflicts: list[GoldConflict] = Field(default_factory=list)
    expected_unknowns: list[str] = Field(default_factory=list)
    gold_facts: list[GoldFact] = Field(default_factory=list)
    expected_current_values: dict[str, str] = Field(default_factory=dict)
    expected_cost_range: CostRange | None = None


class ScenarioMetadata(BaseModel):
    case_type: CaseType
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    primary_metric: str
    gold_version: str = "gold-v1"


class GoldenScenario(BaseModel):
    inputs: ScenarioInputs
    reference_outputs: ScenarioReferenceOutputs
    metadata: ScenarioMetadata


# --------------------------------------------------------------------------
# Frozen Evidence Corpus
# --------------------------------------------------------------------------


class EvidenceRecord(BaseModel):
    evidence_id: str
    company: str
    category: str
    source_type: SourceType
    url: str
    title: str
    published_at: str | None = None
    retrieved_at: str
    content: str
    chunk_id: str
    content_sha256: str


# --------------------------------------------------------------------------
# LLM-as-Judge
# --------------------------------------------------------------------------


class JudgeVerdict(BaseModel):
    """Uniform structured-output contract every judge prompt must produce.
    Judges must reason only from what's handed to them (scenario input,
    reference_outputs, frozen evidence, agent output) — never outside
    knowledge — and must never introduce items (e.g. a red flag) absent from
    both the agent output and the reference."""

    score: float
    passed: bool
    reason: str
    matched_items: list[str] = Field(default_factory=list)
    missed_items: list[str] = Field(default_factory=list)
    unsupported_items: list[str] = Field(default_factory=list)


class QualityJudgeVerdict(BaseModel):
    """Optional aggregate quality judge (see judges/quality_judge.py) — five
    0-4 dimension scores plus rationale; the weighted quality_score is
    computed in Python (evaluators/quality_score.py), never by the judge."""

    factual_correctness: int = Field(ge=0, le=4)
    evidence_faithfulness: int = Field(ge=0, le=4)
    coverage: int = Field(ge=0, le=4)
    conflict_handling: int = Field(ge=0, le=4)
    red_flag_handling: int = Field(ge=0, le=4)
    reason: str


# --------------------------------------------------------------------------
# Experiment metadata / release gates / reporting
# --------------------------------------------------------------------------


class ExperimentMetadata(BaseModel):
    golden_dataset_version: str
    evidence_corpus_version: str
    git_commit_sha: str
    llm_model: str
    judge_model: str
    embedding_model: str
    prompt_version: str
    retrieval_top_k: int
    chunk_size: int
    chunk_overlap: int
    temperature: float
    experiment_timestamp: str
    repetitions: int = 1
    mode: Literal["frozen", "live"] = "frozen"


class MetricResult(BaseModel):
    name: str
    value: float
    required_threshold: float | None = None
    preferred_threshold: float | None = None
    higher_is_better: bool = True
    passed: bool | None = None
    sample_size: int | None = None
    details: dict = Field(default_factory=dict)


class ReleaseGateThresholds(BaseModel):
    critical_red_flag_recall: float = 1.00
    red_flag_recall: float = 0.90
    retrieval_precision_at_5: float = 0.70
    retrieval_recall_at_5: float = 0.85
    ground_truth_coverage: float = 0.85
    conflict_resolution: float = 0.90
    faithfulness: float = 0.90
    unsupported_claim_rate: float = 0.05  # lower is better
    cost_projection_error: float = 0.20  # lower is better
    p95_latency_seconds: float = 60.0  # lower is better
    partial_failure_correctness: float = 1.00

    # Preferred (aspirational) targets — used for WARNING vs PASS distinction
    # when a metric clears required_threshold but misses this one.
    preferred_red_flag_recall: float = 0.95
    preferred_retrieval_precision_at_5: float = 0.80
    preferred_retrieval_recall_at_5: float = 0.90
    preferred_ground_truth_coverage: float = 0.90
    preferred_conflict_resolution: float = 0.95
    preferred_faithfulness: float = 0.95
    preferred_unsupported_claim_rate: float = 0.02
    preferred_cost_projection_error: float = 0.10
    preferred_p95_latency_seconds: float = 45.0


class FailedScenario(BaseModel):
    scenario_id: str
    metric: str
    expected: str
    actual: str
    explanation: str
    evidence_ids: list[str] = Field(default_factory=list)


class ReleaseGateResult(BaseModel):
    status: Literal["PASS", "WARNING", "FAIL"]
    hard_fail: bool = False
    failed_metrics: list[str] = Field(default_factory=list)
    warning_metrics: list[str] = Field(default_factory=list)
    metrics: dict[str, MetricResult] = Field(default_factory=dict)
    failed_scenarios: list[FailedScenario] = Field(default_factory=list)


class EvalReport(BaseModel):
    experiment_metadata: ExperimentMetadata
    thresholds: ReleaseGateThresholds
    gate_result: ReleaseGateResult
    scenario_count: int
    execution_count: int
