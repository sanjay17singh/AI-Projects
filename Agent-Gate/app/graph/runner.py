"""Starts and resumes evaluation runs against the compiled LangGraph workflow.

Every run starts against the *vulnerable* Target Support Agent config — that
is the change under evaluation. If a critical finding is confirmed and a
guardrail is approved, the Orchestrator switches active_target_config to
"guarded" for the re-execution pass.
"""

import uuid

from langgraph.types import Command
from sqlalchemy import select

from app.db.models import EvaluationRunModel
from app.db.repository import create_evaluation_run, create_proposed_change, update_run_status
from app.dependencies import AgentDeps
from app.graph.workflow import build_graph
from app.retrieval.fallback import SEMANTIC_DEGRADATION_KINDS
from app.schemas.change import ProposedChange


def _persist_run_status(run_id: str, state: dict, deps: AgentDeps) -> None:
    report = state.get("report")
    infra_issues = state.get("infra_issues", [])
    fields = {
        "status": "paused_for_human_review" if "__interrupt__" in state else state.get("workflow_status", "completed"),
        "semantic_coverage_degraded": any(i.kind in SEMANTIC_DEGRADATION_KINDS for i in infra_issues),
    }
    if report is not None:
        fields["release_decision"] = report.recommendation
    with deps.session_factory.session() as session:
        update_run_status(session, run_id, **fields)
        session.commit()


def _initial_state(run_id: str, change: ProposedChange) -> dict:
    return {
        "run_id": run_id,
        "correlation_id": str(uuid.uuid4()),
        "tenant_id": change.tenant_id,
        "change": change,
        "active_target_config": "vulnerable",
        "loop_count": 0,
        "executions": [],
        "findings": [],
        "guardrail_recommendations": [],
        "human_decisions": [],
        "regression_test_ids": [],
        "infra_issues": [],
        "workflow_status": "running",
    }


def start_evaluation(change: ProposedChange, deps: AgentDeps, checkpointer, idempotency_key: str) -> dict:
    with deps.session_factory.session() as session:
        change_row = create_proposed_change(
            session,
            tenant_id=change.tenant_id,
            change_type=change.change_type,
            title=change.title,
            diff_summary=change.diff_summary,
            raw_payload=change.raw_payload,
            created_by=change.created_by,
        )
        run_row = create_evaluation_run(
            session,
            change_id=change_row.id,
            scenario_budget=deps.settings.default_scenario_budget,
            idempotency_key=idempotency_key,
        )
        session.commit()
        run_id, thread_id = run_row.id, run_row.thread_id

    change = change.model_copy(update={"id": change_row.id})
    graph = build_graph(deps, checkpointer=checkpointer)
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke(_initial_state(run_id, change), config=config)
    _persist_run_status(run_id, result, deps)
    return {"run_id": run_id, "thread_id": thread_id, "state": result}


def resume_evaluation(thread_id: str, decision_payload: dict, deps: AgentDeps, checkpointer) -> dict:
    graph = build_graph(deps, checkpointer=checkpointer)
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke(Command(resume=decision_payload), config=config)

    # thread_id != run_id, so look up the run via the evaluation_runs.thread_id column
    with deps.session_factory.session() as session:
        run_row = session.scalar(select(EvaluationRunModel).where(EvaluationRunModel.thread_id == thread_id))
        run_id = run_row.id if run_row else None
    if run_id:
        _persist_run_status(run_id, result, deps)
    return {"thread_id": thread_id, "state": result}


def get_run_state(thread_id: str, deps: AgentDeps, checkpointer) -> dict:
    graph = build_graph(deps, checkpointer=checkpointer)
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = graph.get_state(config)
    return {"values": snapshot.values, "next": snapshot.next, "tasks": snapshot.tasks}
