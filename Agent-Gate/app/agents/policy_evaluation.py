"""Policy Evaluation Agent.

Deterministic assertions run first and are authoritative: if any deterministic
assertion fails, the scenario is FAILED regardless of what an LLM rubric
judgment says. The LLM is only ever consulted for the scenario's optional
qualitative rubric, and only after every deterministic assertion has already
passed — its verdict can add a low-severity finding, it can never clear a
security/authorization failure.
"""

from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel
from sqlalchemy import select

from app.agents.prompt_loader import load_prompt
from app.db.models import ScenarioExecutionModel
from app.db.repository import record_evidence, record_finding
from app.dependencies import AgentDeps
from app.llm import LLMUnavailableError, build_chat_model, call_structured
from app.policy.deterministic_rules import evaluate_assertions
from app.schemas.execution import ScenarioExecutionResult
from app.schemas.findings import Finding
from app.schemas.human_review import InfraIssue
from app.schemas.state import AgentGateState
from scenarios.catalog import get_scenario
from scenarios.schema import ScenarioDefinition


class RubricJudgment(BaseModel):
    verdict: Literal["pass", "fail"]
    rationale: str
    confidence: float


def _llm_rubric_judgment(execution: ScenarioExecutionResult, scenario: ScenarioDefinition, deps: AgentDeps) -> RubricJudgment | None:
    if not scenario.llm_rubric:
        return None
    try:
        model = build_chat_model(deps.settings, temperature=0.0, callbacks=deps.tracing_callbacks)
        messages = [
            SystemMessage(content=load_prompt("policy_evaluation_rubric")),
            HumanMessage(
                content=(
                    f"Expected behavior: {scenario.expected_behavior}\n"
                    f"Rubric: {scenario.llm_rubric}\n"
                    f"Target agent final response: {execution.final_output}"
                )
            ),
        ]
        return call_structured(model, RubricJudgment, messages)
    except LLMUnavailableError:
        return None


def evaluate_execution(
    execution: ScenarioExecutionResult, scenario: ScenarioDefinition, deps: AgentDeps
) -> tuple[list[Finding], list[dict], bool]:
    """Returns (findings, evidence_payloads, llm_unavailable).

    At most one Finding is produced per scenario execution: a scenario either
    failed (aggregating every failed assertion into one description, since
    they usually share a single root cause) or it didn't. This keeps
    downstream guardrail recommendations 1:1 with an actual failure instead
    of fragmenting one root cause into several redundant recommendations.
    """
    assertion_results = evaluate_assertions(execution, scenario)
    deterministic_failures = [r for r in assertion_results if not r.passed]

    findings: list[Finding] = []
    evidence_payloads: list[dict] = []
    llm_unavailable = False

    if deterministic_failures:
        description = "; ".join(f"{r.assertion_type}: {r.detail}" for r in deterministic_failures)
        findings.append(
            Finding(
                id="",
                run_id=execution.run_id,
                scenario_execution_id="",
                scenario_id=scenario.id,
                severity=scenario.risk_level,
                category=scenario.category,
                assertion_source="deterministic",
                description=description,
            )
        )
        evidence_payloads.append(
            {
                "assertions": [r.model_dump() for r in deterministic_failures],
                "transcript": [m.model_dump() for m in execution.transcript],
            }
        )

    if not deterministic_failures:
        judgment = _llm_rubric_judgment(execution, scenario, deps)
        if judgment is None and scenario.llm_rubric:
            llm_unavailable = True
        elif judgment is not None and judgment.verdict == "fail":
            findings.append(
                Finding(
                    id="",
                    run_id=execution.run_id,
                    scenario_execution_id="",
                    scenario_id=scenario.id,
                    severity="low",
                    category=scenario.category,
                    assertion_source="llm",
                    description=f"rubric failed: {judgment.rationale} (confidence={judgment.confidence:.2f})",
                )
            )
            evidence_payloads.append({"rubric_judgment": judgment.model_dump()})

    return findings, evidence_payloads, llm_unavailable


def run(state: AgentGateState, deps: AgentDeps) -> dict:
    all_executions = state.get("executions", [])
    latest_attempt = max((e.attempt for e in all_executions), default=1)
    current_executions = [e for e in all_executions if e.attempt == latest_attempt]

    findings: list[Finding] = []
    infra_issues: list[InfraIssue] = []

    with deps.session_factory.session() as session:
        for execution in current_executions:
            scenario = get_scenario(execution.scenario_id)
            scenario_findings, evidence_payloads, llm_unavailable = evaluate_execution(execution, scenario, deps)
            if llm_unavailable:
                infra_issues.append(
                    InfraIssue(kind="openai_unavailable", failure_class="infrastructure", detail=f"rubric judgment skipped for {scenario.id}")
                )

            execution_row = session.scalar(
                select(ScenarioExecutionModel).where(
                    ScenarioExecutionModel.run_id == execution.run_id,
                    ScenarioExecutionModel.scenario_id == execution.scenario_id,
                    ScenarioExecutionModel.attempt == execution.attempt,
                )
            )
            for finding, evidence_payload in zip(scenario_findings, evidence_payloads, strict=True):
                finding_row = record_finding(
                    session,
                    run_id=finding.run_id,
                    scenario_execution_id=execution_row.id if execution_row else "",
                    scenario_id=finding.scenario_id,
                    severity=finding.severity,
                    category=finding.category,
                    assertion_source=finding.assertion_source,
                    description=finding.description,
                )
                record_evidence(
                    session,
                    finding_id=finding_row.id,
                    scenario_execution_id=execution_row.id if execution_row else None,
                    evidence_type="assertion_failure",
                    content=evidence_payload,
                )
                finding.id = finding_row.id
                finding.scenario_execution_id = execution_row.id if execution_row else ""
                findings.append(finding)

        session.commit()

    return {"findings": findings, "infra_issues": infra_issues}
