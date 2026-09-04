"""Guardrail Recommendation Agent: proposes specific repairs for confirmed findings.

Never applies anything — it only writes a `proposed` recommendation. Applying
a guardrail always requires a separate human approval, enforced by the
Orchestrator before any re-execution happens.
"""

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from app.agents.prompt_loader import load_prompt
from app.db.repository import create_guardrail_recommendation
from app.dependencies import AgentDeps
from app.llm import LLMUnavailableError, build_chat_model, call_structured
from app.schemas.findings import Finding
from app.schemas.guardrail import GuardrailRecommendation
from app.schemas.human_review import InfraIssue
from app.schemas.state import AgentGateState
from scenarios.catalog import get_scenario


class GuardrailLLMOutput(BaseModel):
    proposed_change: str
    benefit: str
    side_effects: str
    validation_scenarios: list[str]
    rollback_guidance: str


def _recommend(finding: Finding, deps: AgentDeps) -> GuardrailLLMOutput:
    scenario = get_scenario(finding.scenario_id)
    model = build_chat_model(deps.settings, temperature=0.0, callbacks=deps.tracing_callbacks)
    messages = [
        SystemMessage(content=load_prompt("guardrail_recommendation")),
        HumanMessage(
            content=(
                f"Scenario: {scenario.id} - {scenario.title}\n"
                f"Category: {scenario.category}, risk level: {scenario.risk_level}\n"
                f"Forbidden behavior: {scenario.forbidden_behavior}\n"
                f"Finding: {finding.description}"
            )
        ),
    ]
    return call_structured(model, GuardrailLLMOutput, messages)


def run(state: AgentGateState, deps: AgentDeps) -> dict:
    findings = state.get("findings", [])
    existing_finding_ids = {g.finding_id for g in state.get("guardrail_recommendations", [])}
    open_deterministic = [
        f for f in findings if f.status == "open" and f.assertion_source == "deterministic" and f.id not in existing_finding_ids
    ]

    recommendations: list[GuardrailRecommendation] = []
    infra_issues: list[InfraIssue] = []

    with deps.session_factory.session() as session:
        for finding in open_deterministic:
            try:
                output = _recommend(finding, deps)
            except LLMUnavailableError as exc:
                infra_issues.append(
                    InfraIssue(kind="openai_unavailable", failure_class="infrastructure", detail=str(exc))
                )
                continue

            row = create_guardrail_recommendation(
                session,
                run_id=state["run_id"],
                finding_id=finding.id,
                failure_summary=finding.description,
                proposed_change=output.proposed_change,
                benefit=output.benefit,
                side_effects=output.side_effects,
                validation_scenarios=output.validation_scenarios,
                rollback_guidance=output.rollback_guidance,
            )
            recommendations.append(
                GuardrailRecommendation(
                    id=row.id,
                    run_id=row.run_id,
                    finding_id=row.finding_id,
                    failure_summary=row.failure_summary,
                    proposed_change=row.proposed_change,
                    benefit=row.benefit,
                    side_effects=row.side_effects,
                    validation_scenarios=row.validation_scenarios,
                    rollback_guidance=row.rollback_guidance,
                    status=row.status,
                )
            )
        session.commit()

    return {"guardrail_recommendations": recommendations, "infra_issues": infra_issues}
