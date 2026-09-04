"""If a human rejects the proposed guardrail, the workflow must not apply it
and must go straight to report generation with the finding still unresolved
(BLOCK-worthy), never looping back for a second attempt.
"""

import uuid

from sqlalchemy import select

from app.db.models import GuardrailRecommendationModel, RegressionTestModel
from app.demo.fakes import (
    patch_all_llm_calls,
    patch_scenario_selection,
    patch_target_agent_execution,
)
from app.graph.runner import resume_evaluation, start_evaluation
from app.schemas.change import ProposedChange


def test_guardrail_rejection_routes_to_report_without_applying_fix(monkeypatch, deps, checkpointer):
    patch_all_llm_calls(monkeypatch)
    patch_scenario_selection(monkeypatch, ["ADV-INJ-INDIRECT-01"])
    patch_target_agent_execution(monkeypatch)

    change = ProposedChange(
        id="", tenant_id="default", change_type="retrieval", title="t", diff_summary="d", raw_payload={}, created_by="tester"
    )
    outcome = start_evaluation(change, deps, checkpointer, f"run-{uuid.uuid4()}")
    assert "__interrupt__" in outcome["state"]
    assert outcome["state"]["__interrupt__"][0].value["review_type"] == "guardrail"

    resume = resume_evaluation(
        outcome["thread_id"],
        {"reviewer": "reviewer@test", "decision": "reject", "justification": "Not the right fix; needs more design work."},
        deps,
        checkpointer,
    )
    state = resume["state"]

    # rejection is high-risk enough to still require a final release decision (which will be BLOCK)
    assert "__interrupt__" in state
    assert state["__interrupt__"][0].value["review_type"] == "release_override"

    with deps.session_factory.session() as session:
        guardrails = session.scalars(
            select(GuardrailRecommendationModel).where(GuardrailRecommendationModel.run_id == outcome["run_id"])
        ).all()
        assert guardrails[0].status == "rejected"

        regression_tests = session.scalars(
            select(RegressionTestModel).where(RegressionTestModel.origin_run_id == outcome["run_id"])
        ).all()
        assert regression_tests == [], "a rejected guardrail must never produce a regression test"

    final = resume_evaluation(
        outcome["thread_id"],
        {"reviewer": "reviewer@test", "decision": "approve", "justification": "Acknowledging the block."},
        deps,
        checkpointer,
    )
    assert "__interrupt__" not in final["state"]
    assert final["state"]["report"].recommendation == "BLOCK"
