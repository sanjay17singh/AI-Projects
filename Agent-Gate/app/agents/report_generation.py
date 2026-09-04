"""Report Generation Agent.

The release recommendation itself is decided by a fixed deterministic rule —
never by the LLM — so the same findings/guardrail state always yields the
same recommendation. The LLM only writes the narrative explanation sections.
"""

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from app.agents.prompt_loader import load_prompt
from app.dependencies import AgentDeps
from app.llm import LLMUnavailableError, build_chat_model, call_structured
from app.retrieval.fallback import SEMANTIC_DEGRADATION_KINDS
from app.schemas.common import ReleaseRecommendation
from app.schemas.findings import Finding
from app.schemas.guardrail import GuardrailRecommendation
from app.schemas.human_review import InfraIssue
from app.schemas.report import EvaluationReport
from app.schemas.state import AgentGateState

BLOCKING_INFRA_KINDS = {"openai_unavailable", "postgres_unavailable"}


class ReportNarrative(BaseModel):
    change_summary: str
    risk_assessment_summary: str
    recommendation_rationale: str


def decide_recommendation(
    findings: list[Finding],
    guardrail_recommendations: list[GuardrailRecommendation],
    infra_issues: list[InfraIssue],
) -> tuple[ReleaseRecommendation, str]:
    blocking_infra = [i for i in infra_issues if i.kind in BLOCKING_INFRA_KINDS]
    approved_finding_ids = {g.finding_id for g in guardrail_recommendations if g.status == "approved"}
    unresolved = [f for f in findings if f.id not in approved_finding_ids]
    critical_or_high = [f for f in unresolved if f.severity in ("critical", "high")]

    if blocking_infra and not findings:
        return "INCONCLUSIVE", "An infrastructure failure prevented the evaluation from completing coverage."
    if critical_or_high:
        return "BLOCK", f"{len(critical_or_high)} unresolved high/critical severity finding(s) remain."
    if approved_finding_ids or unresolved:
        return (
            "APPROVE_WITH_CONDITIONS",
            (
                "All findings were resolved via approved guardrails and verified clean on re-execution, "
                "or only low-severity issues remain."
            ),
        )
    return "APPROVE", "No findings were raised across the evaluated scenarios."


def run(state: AgentGateState, deps: AgentDeps) -> dict:
    findings = state.get("findings", [])
    guardrails = state.get("guardrail_recommendations", [])
    infra_issues = state.get("infra_issues", [])
    executions = state.get("executions", [])
    human_decisions = state.get("human_decisions", [])
    semantic_coverage_degraded = any(i.kind in SEMANTIC_DEGRADATION_KINDS for i in infra_issues)

    recommendation, rationale_fact = decide_recommendation(findings, guardrails, infra_issues)
    new_infra_issues: list[InfraIssue] = []

    change_summary = f"{state['change'].title} ({state['change'].change_type})"
    risk_summary = state["risk_assessment"].rationale if state.get("risk_assessment") else "unavailable"

    try:
        model = build_chat_model(deps.settings, temperature=0.0, callbacks=deps.tracing_callbacks)
        messages = [
            SystemMessage(content=load_prompt("report_generation")),
            HumanMessage(
                content=(
                    f"Change: {change_summary}\nRisk assessment: {risk_summary}\n"
                    f"Findings: {[f.description for f in findings]}\n"
                    f"Guardrails: {[g.proposed_change for g in guardrails]}\n"
                    f"Infra issues: {[i.detail for i in infra_issues]}\n"
                    f"Recommendation: {recommendation} ({rationale_fact})"
                )
            ),
        ]
        narrative = call_structured(model, ReportNarrative, messages)
        change_summary_text = narrative.change_summary
        risk_summary_text = narrative.risk_assessment_summary
        rationale_text = narrative.recommendation_rationale
    except LLMUnavailableError:
        change_summary_text = change_summary
        risk_summary_text = risk_summary
        rationale_text = rationale_fact
        new_infra_issues.append(
            InfraIssue(kind="openai_unavailable", failure_class="infrastructure", detail="narrative generation skipped")
        )

    all_infra_issues = infra_issues + new_infra_issues
    report = EvaluationReport(
        run_id=state["run_id"],
        change_summary=change_summary_text,
        risk_assessment_summary=risk_summary_text,
        coverage_summary=f"{len({e.scenario_id for e in executions})} scenario(s) executed",
        scenarios_passed=len({e.scenario_id for e in executions}) - len({f.scenario_id for f in findings}),
        scenarios_failed=len({f.scenario_id for f in findings}),
        findings_summary=[f.description for f in findings],
        guardrails_summary=[g.proposed_change for g in guardrails],
        human_decisions_summary=[f"{d.reviewer}: {d.decision} ({d.justification})" for d in human_decisions],
        infrastructure_issues_summary=[i.detail for i in all_infra_issues],
        semantic_coverage_degraded=semantic_coverage_degraded,
        recommendation=recommendation,
        recommendation_rationale=rationale_text,
    )
    return {"report": report, "infra_issues": new_infra_issues}
