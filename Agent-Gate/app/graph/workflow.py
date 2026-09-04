"""Assembles the AgentGate LangGraph workflow.

Start -> Change Analysis -> Scenario Design -> budget check
  -> (over budget) human review (budget) -> proceed/abort
  -> Sandbox Execution -> Policy Evaluation
    -> (no findings) Report Generation
    -> (findings) Guardrail Recommendation -> human review (guardrail)
       -> (approved) apply guarded config -> Sandbox Execution [re-entry, bounded to 1]
       -> (rejected) Report Generation
  -> (re-entry clean) Regression Test -> Report Generation
  -> (re-entry still failing) Report Generation
-> final human release review -> END

Every conditional edge here delegates its decision to app/agents/orchestrator.py —
this module only wires nodes together, it contains no routing logic itself.
"""

from functools import partial

from langgraph.graph import END, START, StateGraph

from app.agents import (
    change_analysis,
    guardrail_recommendation,
    orchestrator,
    policy_evaluation,
    regression_test,
    report_generation,
    sandbox_execution,
    scenario_design,
)
from app.db.repository import create_release_decision, update_guardrail_status
from app.dependencies import AgentDeps
from app.schemas.report import EvaluationReport
from app.schemas.state import AgentGateState


def _budget_review_node(state: AgentGateState, deps: AgentDeps) -> dict:
    result = orchestrator.request_human_review(
        state,
        deps,
        review_type="budget",
        evidence_ref=f"budget:{state['run_id']}",
        available_actions=["approve", "reject"],
        idempotency_key=f"budget:{state['run_id']}",
    )
    decision = result["human_decisions"][-1]
    budget = state["budget"]
    if decision.decision == "approve" and budget is not None:
        result["budget"] = budget.model_copy(update={"exceeds_budget": False, "approved_by": decision.reviewer})
        result["workflow_status"] = "budget_approved"
    return result


def _budget_rejected_report_node(state: AgentGateState, deps: AgentDeps) -> dict:
    report = EvaluationReport(
        run_id=state["run_id"],
        change_summary=f"{state['change'].title} ({state['change'].change_type})",
        risk_assessment_summary=state["risk_assessment"].rationale if state.get("risk_assessment") else "unavailable",
        coverage_summary="0 scenarios executed: evaluation budget increase was rejected",
        scenarios_passed=0,
        scenarios_failed=0,
        findings_summary=[],
        guardrails_summary=[],
        human_decisions_summary=[f"{d.reviewer}: {d.decision} ({d.justification})" for d in state.get("human_decisions", [])],
        infrastructure_issues_summary=[],
        semantic_coverage_degraded=False,
        recommendation="INCONCLUSIVE",
        recommendation_rationale="The requested evaluation scope exceeded the approved budget and the increase was rejected, so no scenarios were executed.",
    )
    return {"report": report, "workflow_status": "budget_rejected"}


def _guardrail_review_node(state: AgentGateState, deps: AgentDeps) -> dict:
    new_findings = [f for f in state.get("findings", []) if f.status == "open"]
    finding_ref = new_findings[0].id if new_findings else state["run_id"]
    result = orchestrator.request_human_review(
        state,
        deps,
        review_type="guardrail",
        evidence_ref=f"guardrail:{finding_ref}",
        available_actions=["approve", "reject"],
        idempotency_key=f"guardrail:{finding_ref}",
    )
    decision = result["human_decisions"][-1]
    new_status = "approved" if decision.decision == "approve" else "rejected"

    open_guardrails = [g for g in state.get("guardrail_recommendations", []) if g.status == "proposed"]
    with deps.session_factory.session() as session:
        for g in open_guardrails:
            update_guardrail_status(session, g.id, new_status)
        session.commit()

    result["guardrail_recommendations"] = [
        g.model_copy(update={"status": new_status}) if g.status == "proposed" else g
        for g in state.get("guardrail_recommendations", [])
    ]
    result["workflow_status"] = "guardrail_rejected" if new_status == "rejected" else "guardrail_approved"
    return result


def _apply_guarded_config_node(state: AgentGateState, deps: AgentDeps) -> dict:
    return {
        "active_target_config": "guarded",
        "loop_count": state.get("loop_count", 0) + 1,
        "workflow_status": "resumed_from_checkpoint",
    }


def _final_release_review_node(state: AgentGateState, deps: AgentDeps) -> dict:
    report = state["report"]
    if orchestrator.release_requires_human_review(state):
        review_type = "release_override" if report.recommendation in ("BLOCK", "INCONCLUSIVE") else "release"
        result = orchestrator.request_human_review(
            state,
            deps,
            review_type=review_type,
            evidence_ref=f"release:{state['run_id']}",
            available_actions=["approve", "reject"],
            idempotency_key=f"release:{state['run_id']}",
        )
        decision = result["human_decisions"][-1]
        final_recommendation = report.recommendation if decision.decision == "approve" else "BLOCK"
        decided_by = decision.reviewer
    else:
        result = {}
        final_recommendation = report.recommendation
        decided_by = "system-auto"

    with deps.session_factory.session() as session:
        create_release_decision(
            session,
            run_id=state["run_id"],
            recommendation=final_recommendation,
            decided_by=decided_by,
            idempotency_key=f"release-decision:{state['run_id']}",
        )
        session.commit()

    result["workflow_status"] = "completed"
    return result


def build_graph(deps: AgentDeps, checkpointer=None):
    graph = StateGraph(AgentGateState)

    graph.add_node("change_analysis", partial(change_analysis.run, deps=deps))
    graph.add_node("scenario_design", partial(scenario_design.run, deps=deps))
    graph.add_node("budget_review", partial(_budget_review_node, deps=deps))
    graph.add_node("budget_rejected_report", partial(_budget_rejected_report_node, deps=deps))
    graph.add_node("sandbox_execution", partial(sandbox_execution.run, deps=deps))
    graph.add_node("policy_evaluation", partial(policy_evaluation.run, deps=deps))
    graph.add_node("guardrail_recommendation", partial(guardrail_recommendation.run, deps=deps))
    graph.add_node("guardrail_review", partial(_guardrail_review_node, deps=deps))
    graph.add_node("apply_guarded_config", partial(_apply_guarded_config_node, deps=deps))
    graph.add_node("regression_test", partial(regression_test.run, deps=deps))
    graph.add_node("report_generation", partial(report_generation.run, deps=deps))
    graph.add_node("final_release_review", partial(_final_release_review_node, deps=deps))

    graph.add_edge(START, "change_analysis")
    graph.add_edge("change_analysis", "scenario_design")

    graph.add_conditional_edges(
        "scenario_design",
        orchestrator.route_after_budget_check,
        {"within_budget": "sandbox_execution", "needs_approval": "budget_review"},
    )
    graph.add_conditional_edges(
        "budget_review",
        orchestrator.route_after_budget_review,
        {"proceed": "sandbox_execution", "abort": "budget_rejected_report"},
    )
    graph.add_edge("budget_rejected_report", END)

    graph.add_edge("sandbox_execution", "policy_evaluation")
    graph.add_conditional_edges(
        "policy_evaluation",
        orchestrator.route_after_policy_evaluation,
        {
            "first_pass_clean": "report_generation",
            "first_pass_findings": "guardrail_recommendation",
            "reentry_clean": "regression_test",
            "reentry_findings": "report_generation",
        },
    )
    graph.add_edge("guardrail_recommendation", "guardrail_review")
    graph.add_conditional_edges(
        "guardrail_review",
        orchestrator.route_after_guardrail_review,
        {"approved": "apply_guarded_config", "rejected": "report_generation"},
    )
    graph.add_edge("apply_guarded_config", "sandbox_execution")
    graph.add_edge("regression_test", "report_generation")
    graph.add_edge("report_generation", "final_release_review")
    graph.add_edge("final_release_review", END)

    return graph.compile(checkpointer=checkpointer)
