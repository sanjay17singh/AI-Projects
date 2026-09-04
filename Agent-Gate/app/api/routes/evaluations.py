from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.api.deps import get_agent_deps, get_request_checkpointer
from app.api.schemas import CreateEvaluationRequest, CreateEvaluationResponse
from app.db.repository import (
    get_run,
    list_findings,
    list_runs_with_change,
    list_scenario_executions,
)
from app.dependencies import AgentDeps
from app.graph.runner import start_evaluation
from app.schemas.change import ProposedChange

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


def _pending_review(state: dict) -> dict | None:
    interrupts = state.get("__interrupt__")
    if not interrupts:
        return None
    return dict(interrupts[0].value)


def _serialize(value):
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_serialize(v) for v in value]
    if isinstance(value, dict):
        return {k: _serialize(v) for k, v in value.items() if k != "__interrupt__"}
    return value


@router.post("", response_model=CreateEvaluationResponse)
def create_evaluation(
    body: CreateEvaluationRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    deps: AgentDeps = Depends(get_agent_deps),
    checkpointer=Depends(get_request_checkpointer),
):
    change = ProposedChange(
        id="",
        tenant_id=body.tenant_id,
        change_type=body.change_type,
        title=body.title,
        diff_summary=body.diff_summary,
        raw_payload=body.raw_payload,
        created_by=body.created_by,
    )
    outcome = start_evaluation(change, deps, checkpointer, idempotency_key)
    pending = _pending_review(outcome["state"])
    return CreateEvaluationResponse(
        run_id=outcome["run_id"],
        thread_id=outcome["thread_id"],
        status="paused_for_human_review" if pending else outcome["state"].get("workflow_status", "completed"),
        pending_review=pending,
    )


@router.get("")
def list_evaluations(deps: AgentDeps = Depends(get_agent_deps)):
    with deps.session_factory.session() as session:
        rows = list_runs_with_change(session)
        return [
            {
                "run_id": run.id,
                "title": change.title,
                "change_type": change.change_type,
                "status": run.status,
                "release_decision": run.release_decision,
                "semantic_coverage_degraded": run.semantic_coverage_degraded,
                "created_at": run.created_at,
            }
            for run, change in rows
        ]


@router.get("/{run_id}")
def get_evaluation(run_id: str, deps: AgentDeps = Depends(get_agent_deps)):
    with deps.session_factory.session() as session:
        run = get_run(session, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="evaluation run not found")
        return {
            "run_id": run.id,
            "status": run.status,
            "scenario_budget": run.scenario_budget,
            "budget_approved": run.budget_approved,
            "semantic_coverage_degraded": run.semantic_coverage_degraded,
            "release_decision": run.release_decision,
            "created_at": run.created_at,
            "updated_at": run.updated_at,
        }


@router.get("/{run_id}/scenarios")
def get_evaluation_scenarios(run_id: str, deps: AgentDeps = Depends(get_agent_deps)):
    with deps.session_factory.session() as session:
        executions = list_scenario_executions(session, run_id)
        return [
            {
                "scenario_id": e.scenario_id,
                "attempt": e.attempt,
                "target_config": e.target_config,
                "status": e.status,
                "latency_ms": e.latency_ms,
                "error": e.error,
                "tool_calls": e.tool_calls,
            }
            for e in executions
        ]


@router.get("/{run_id}/findings")
def get_evaluation_findings(run_id: str, deps: AgentDeps = Depends(get_agent_deps)):
    with deps.session_factory.session() as session:
        findings = list_findings(session, run_id)
        return [
            {
                "id": f.id,
                "scenario_id": f.scenario_id,
                "severity": f.severity,
                "category": f.category,
                "assertion_source": f.assertion_source,
                "description": f.description,
                "status": f.status,
            }
            for f in findings
        ]


@router.get("/{run_id}/state")
def get_evaluation_state(
    run_id: str,
    deps: AgentDeps = Depends(get_agent_deps),
    checkpointer=Depends(get_request_checkpointer),
):
    from app.graph.runner import get_run_state

    with deps.session_factory.session() as session:
        run = get_run(session, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="evaluation run not found")
        thread_id = run.thread_id

    snapshot = get_run_state(thread_id, deps, checkpointer)
    values = {k: v for k, v in snapshot["values"].items() if k != "change"}

    pending_interrupts = [t.interrupts[0] for t in snapshot["tasks"] if t.interrupts]
    pending_review = _pending_review({"__interrupt__": pending_interrupts}) if pending_interrupts else None

    return {
        "values": _serialize(values),
        "next_nodes": list(snapshot["next"]),
        "pending_review": pending_review,
    }


@router.get("/{run_id}/report")
def get_evaluation_report(
    run_id: str,
    deps: AgentDeps = Depends(get_agent_deps),
    checkpointer=Depends(get_request_checkpointer),
):
    from app.graph.runner import get_run_state

    with deps.session_factory.session() as session:
        run = get_run(session, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="evaluation run not found")
        thread_id = run.thread_id

    snapshot = get_run_state(thread_id, deps, checkpointer)
    report = snapshot["values"].get("report")
    if report is None:
        raise HTTPException(status_code=404, detail="report not yet available for this run")
    return report.model_dump() if hasattr(report, "model_dump") else report
