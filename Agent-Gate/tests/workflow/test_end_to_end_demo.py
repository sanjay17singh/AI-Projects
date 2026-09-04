"""End-to-end reproduction of the primary demonstration: indirect prompt
injection triggers an unauthorized $500 refund, AgentGate's deterministic
policy layer catches it, a guardrail is proposed and approved, the guarded
config is re-verified clean, a regression test is created, and the final
release decision requires human sign-off.

The LLM and Target Support Agent execution are faked (see app/demo/fakes.py —
the same fakes scripts/run_demo.py falls back to without live credentials)
so this test needs no OpenAI/Pinecone credentials — it exercises the graph's
control flow, the deterministic policy engine, and Postgres persistence for real.
"""

import uuid

from sqlalchemy import select

from app.db.models import (
    EvaluationRunModel,
    FindingModel,
    GuardrailRecommendationModel,
    RegressionTestModel,
    ReleaseDecisionModel,
)
from app.demo.fakes import (
    patch_all_llm_calls,
    patch_scenario_selection,
    patch_target_agent_execution,
)
from app.graph.runner import resume_evaluation, start_evaluation
from app.schemas.change import ProposedChange


def _make_change() -> ProposedChange:
    return ProposedChange(
        id="",
        tenant_id="default",
        change_type="retrieval",
        title="Enable knowledge-base retrieval for refund FAQ answers",
        diff_summary="The support agent now retrieves knowledge-base documents to answer refund policy questions.",
        raw_payload={},
        created_by="it@intellious.tech",
    )


def test_primary_demo_end_to_end(monkeypatch, deps, checkpointer):
    patch_all_llm_calls(monkeypatch)
    patch_scenario_selection(monkeypatch, ["ADV-INJ-INDIRECT-01"])
    patch_target_agent_execution(monkeypatch)

    idempotency_key = f"test-run-{uuid.uuid4()}"
    change = _make_change()

    # Step 1: kick off the run. No budget interrupt expected (1 planned scenario, budget=40).
    outcome = start_evaluation(change, deps, checkpointer, idempotency_key)
    state = outcome["state"]
    assert "__interrupt__" in state, "expected the graph to pause for guardrail approval"
    interrupt = state["__interrupt__"][0]
    assert interrupt.value["review_type"] == "guardrail"

    # The vulnerable agent's $500 refund should already be a confirmed, persisted finding.
    with deps.session_factory.session() as session:
        findings = session.scalars(select(FindingModel).where(FindingModel.run_id == outcome["run_id"])).all()
        assert any(f.category == "adversarial_indirect_injection" for f in findings)
        guardrails = session.scalars(
            select(GuardrailRecommendationModel).where(GuardrailRecommendationModel.run_id == outcome["run_id"])
        ).all()
        assert len(guardrails) == 1
        assert guardrails[0].status == "proposed"

    # Step 2: human approves the guardrail.
    resume1 = resume_evaluation(
        outcome["thread_id"],
        {"reviewer": "it@intellious.tech", "decision": "approve", "justification": "Confirmed root cause; approving the identity/refund-cap fix."},
        deps,
        checkpointer,
    )
    state2 = resume1["state"]
    assert "__interrupt__" in state2, "expected the graph to pause again for the final release decision"
    release_interrupt = state2["__interrupt__"][0]
    assert release_interrupt.value["review_type"] in ("release", "release_override")

    with deps.session_factory.session() as session:
        guardrails = session.scalars(
            select(GuardrailRecommendationModel).where(GuardrailRecommendationModel.run_id == outcome["run_id"])
        ).all()
        assert guardrails[0].status == "approved"

        regression_tests = session.scalars(
            select(RegressionTestModel).where(RegressionTestModel.origin_run_id == outcome["run_id"])
        ).all()
        assert len(regression_tests) == 1, "the confirmed, now-mitigated failure should become a regression test"

        mitigated = session.scalars(
            select(FindingModel).where(FindingModel.run_id == outcome["run_id"], FindingModel.status == "mitigated")
        ).all()
        assert len(mitigated) >= 1

    report = state2["report"]
    assert report.recommendation == "APPROVE_WITH_CONDITIONS"

    # Step 3: human makes the final release decision.
    resume2 = resume_evaluation(
        outcome["thread_id"],
        {"reviewer": "it@intellious.tech", "decision": "approve", "justification": "Guardrail verified effective; approving release."},
        deps,
        checkpointer,
    )
    final_state = resume2["state"]
    assert "__interrupt__" not in final_state
    assert final_state["workflow_status"] == "completed"

    with deps.session_factory.session() as session:
        run_row = session.get(EvaluationRunModel, outcome["run_id"])
        release = session.scalars(
            select(ReleaseDecisionModel).where(ReleaseDecisionModel.run_id == outcome["run_id"])
        ).one()
        assert release.recommendation == "APPROVE_WITH_CONDITIONS"
        assert release.decided_by == "it@intellious.tech"

        assert run_row is not None
        assert run_row.status is not None
