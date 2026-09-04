"""When Scenario Design's planned coverage exceeds the approved budget, the
workflow must pause for a budget-increase approval before Sandbox Execution
runs at all. Rejecting the increase aborts with INCONCLUSIVE and zero
scenario executions; approving lets it proceed.
"""

import uuid

from app.demo.fakes import patch_all_llm_calls, patch_target_agent_execution
from app.graph.runner import resume_evaluation, start_evaluation
from app.schemas.change import ProposedChange


def _make_change():
    return ProposedChange(
        id="", tenant_id="default", change_type="retrieval", title="t", diff_summary="d", raw_payload={}, created_by="tester"
    )


def test_budget_exceeded_requests_approval_before_any_execution(monkeypatch, deps, checkpointer):
    patch_all_llm_calls(monkeypatch)
    patch_target_agent_execution(monkeypatch)
    monkeypatch.setattr(deps.settings, "default_scenario_budget", 1)  # 32 scenarios will be selected by default

    outcome = start_evaluation(_make_change(), deps, checkpointer, f"run-{uuid.uuid4()}")
    state = outcome["state"]
    assert "__interrupt__" in state
    assert state["__interrupt__"][0].value["review_type"] == "budget"
    assert state["executions"] == [], "no scenario should execute before the budget is approved"


def test_budget_rejection_aborts_with_inconclusive_and_no_executions(monkeypatch, deps, checkpointer):
    patch_all_llm_calls(monkeypatch)
    patch_target_agent_execution(monkeypatch)
    monkeypatch.setattr(deps.settings, "default_scenario_budget", 1)

    outcome = start_evaluation(_make_change(), deps, checkpointer, f"run-{uuid.uuid4()}")
    resume = resume_evaluation(
        outcome["thread_id"],
        {"reviewer": "reviewer@test", "decision": "reject", "justification": "Scope too broad for this cycle."},
        deps,
        checkpointer,
    )
    state = resume["state"]
    assert "__interrupt__" not in state
    assert state["report"].recommendation == "INCONCLUSIVE"
    assert state["executions"] == []


def test_budget_approval_proceeds_to_execution(monkeypatch, deps, checkpointer):
    patch_all_llm_calls(monkeypatch)
    patch_target_agent_execution(monkeypatch)
    monkeypatch.setattr(deps.settings, "default_scenario_budget", 1)

    outcome = start_evaluation(_make_change(), deps, checkpointer, f"run-{uuid.uuid4()}")
    resume = resume_evaluation(
        outcome["thread_id"],
        {"reviewer": "reviewer@test", "decision": "approve", "justification": "Broad coverage is warranted here."},
        deps,
        checkpointer,
    )
    state = resume["state"]
    assert len(state["executions"]) > 0, "approving the budget should let sandbox execution run"
