"""Scenario Design Agent: selects catalog scenarios, retrieves related context from
Pinecone (degrading gracefully to the local catalog), and proposes a budget.

Selection itself is deterministic (every adversarial scenario is always in
scope as a security floor; benign scenarios are included when their category
matches the Change Analysis Agent's required coverage, or all of them when
coverage requirements are empty/unclear) — the LLM is only used to write a
human-readable rationale, never to decide what gets tested.
"""

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from app.agents.prompt_loader import load_prompt
from app.dependencies import AgentDeps
from app.llm import LLMUnavailableError, build_chat_model, call_structured
from app.retrieval.fallback import retrieve_with_fallback
from app.schemas.change import RiskAssessment
from app.schemas.execution import BudgetStatus, ScenarioPlanItem
from app.schemas.human_review import InfraIssue
from app.schemas.state import AgentGateState
from scenarios.catalog import load_catalog


class ScenarioRationale(BaseModel):
    rationale: str


def select_scenarios(risk_assessment: RiskAssessment | None) -> list[ScenarioPlanItem]:
    catalog = load_catalog()
    required = {c.lower() for c in (risk_assessment.required_coverage_categories if risk_assessment else [])}

    planned = []
    for scenario in catalog:
        if scenario.bucket == "adversarial":
            include, rationale = True, "adversarial scenarios are always in scope as a security floor"
        elif scenario.bucket == "benign":
            matches = not required or any(req in scenario.category for req in required)
            include, rationale = matches, "matches required coverage category" if required else "no coverage constraint supplied; including full benign suite"
        else:
            include, rationale = False, "resilience scenarios validate AgentGate's own workflow, not a specific change"
        if include:
            planned.append(
                ScenarioPlanItem(
                    scenario_id=scenario.id, category=scenario.category, risk_level=scenario.risk_level, rationale=rationale
                )
            )
    return planned


def run(state: AgentGateState, deps: AgentDeps) -> dict:
    risk_assessment = state.get("risk_assessment")
    planned = select_scenarios(risk_assessment)

    infra_issues = []
    outcome = retrieve_with_fallback(
        deps.retriever,
        tenant_id=state.get("tenant_id", "default"),
        query_text=state["change"].diff_summary,
        doc_type="prior_failure",
    )
    if outcome.degraded:
        infra_issues.append(
            InfraIssue(
                kind=outcome.kind,
                failure_class="infrastructure",
                detail=outcome.reason or "semantic retrieval unavailable",
            )
        )

    approved_budget = deps.settings.default_scenario_budget
    budget = BudgetStatus(
        approved_budget=approved_budget,
        planned_count=len(planned),
        exceeds_budget=len(planned) > approved_budget,
    )

    update: dict = {"planned_scenarios": planned, "budget": budget, "infra_issues": infra_issues}
    if outcome.degraded:
        update["workflow_status"] = "degraded_semantic_coverage"

    try:
        model = build_chat_model(deps.settings, temperature=0.0, callbacks=deps.tracing_callbacks)
        messages = [
            SystemMessage(content=load_prompt("scenario_design_rationale")),
            HumanMessage(
                content=(
                    f"Risk assessment: {risk_assessment.model_dump() if risk_assessment else 'unavailable'}\n"
                    f"Selected scenarios: {[p.scenario_id for p in planned]}\n"
                    f"Semantic retrieval degraded: {outcome.degraded}"
                )
            ),
        ]
        call_structured(model, ScenarioRationale, messages)
    except LLMUnavailableError:
        infra_issues.append(
            InfraIssue(kind="openai_unavailable", failure_class="infrastructure", detail="rationale generation skipped")
        )
        update["infra_issues"] = infra_issues

    return update
