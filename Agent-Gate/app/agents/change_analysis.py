"""Change Analysis Agent: identifies affected behavior, risk, and required coverage."""

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.prompt_loader import load_prompt
from app.dependencies import AgentDeps
from app.llm import LLMUnavailableError, build_chat_model, call_structured
from app.schemas.change import ProposedChange, RiskAssessment
from app.schemas.human_review import InfraIssue
from app.schemas.state import AgentGateState


def analyze_change(change: ProposedChange, deps: AgentDeps) -> RiskAssessment:
    model = build_chat_model(deps.settings, temperature=0.0, callbacks=deps.tracing_callbacks)
    messages = [
        SystemMessage(content=load_prompt("change_analysis")),
        HumanMessage(
            content=(
                f"Change type: {change.change_type}\n"
                f"Title: {change.title}\n"
                f"Diff summary: {change.diff_summary}\n"
                f"Raw payload: {change.raw_payload}"
            )
        ),
    ]
    return call_structured(model, RiskAssessment, messages)


def run(state: AgentGateState, deps: AgentDeps) -> dict:
    change = state["change"]
    try:
        risk_assessment = analyze_change(change, deps)
        return {"risk_assessment": risk_assessment}
    except LLMUnavailableError as exc:
        return {
            "infra_issues": [
                InfraIssue(kind="openai_unavailable", failure_class="infrastructure", detail=str(exc))
            ],
            "workflow_status": "inconclusive_infra_failure",
        }
