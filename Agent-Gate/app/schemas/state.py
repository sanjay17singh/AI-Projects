"""The single typed state object threaded through the LangGraph workflow.

TypedDict (not a Pydantic BaseModel) because LangGraph's state-merging and
checkpointing machinery operates on TypedDict/dataclass state. Every field's
*value* is still a validated Pydantic model — nodes construct/parse those
explicitly, so "typed state" here means both the container shape and every
value inside it are checked, not just duck-typed dicts.
"""

import operator
from typing import Annotated, Literal, TypedDict

from app.schemas.change import ProposedChange, RiskAssessment
from app.schemas.execution import BudgetStatus, ScenarioExecutionResult, ScenarioPlanItem
from app.schemas.findings import Finding
from app.schemas.guardrail import GuardrailRecommendation
from app.schemas.human_review import HumanDecision, HumanReviewRequest, InfraIssue
from app.schemas.report import EvaluationReport


def _upsert_by_id(left: list, right: list) -> list:
    """Merges by `.id`: an incoming item with a matching id replaces the existing
    one (used for entities whose *status* changes over the run, e.g. a
    guardrail recommendation moving from proposed -> approved/rejected),
    everything else is appended.
    """
    by_id = {item.id: item for item in left}
    for item in right:
        by_id[item.id] = item
    return list(by_id.values())


class AgentGateState(TypedDict, total=False):
    run_id: str
    correlation_id: str
    tenant_id: str

    change: ProposedChange
    risk_assessment: RiskAssessment | None

    planned_scenarios: list[ScenarioPlanItem]
    budget: BudgetStatus | None

    active_target_config: Literal["vulnerable", "guarded"]
    loop_count: int

    executions: Annotated[list[ScenarioExecutionResult], operator.add]
    findings: Annotated[list[Finding], _upsert_by_id]
    guardrail_recommendations: Annotated[list[GuardrailRecommendation], _upsert_by_id]

    pending_human_review: HumanReviewRequest | None
    human_decisions: Annotated[list[HumanDecision], operator.add]

    regression_test_ids: Annotated[list[str], operator.add]
    infra_issues: Annotated[list[InfraIssue], operator.add]

    retry_counts: dict[str, int]

    workflow_status: str

    report: EvaluationReport | None
