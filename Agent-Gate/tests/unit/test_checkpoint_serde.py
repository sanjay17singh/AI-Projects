"""Verifies the checkpoint serializer allow-lists every Pydantic type that can
appear in AgentGateState (so LangGraph never logs an "unregistered type" /
future-blocked warning for our own schemas) while still treating anything
outside that list as unregistered — an explicit allowlist, not a blanket
"allow everything" escape hatch.
"""

from datetime import UTC

from pydantic import BaseModel

from app.db.checkpointer import CHECKPOINT_ALLOWED_TYPES, _checkpoint_serde
from app.schemas.execution import ChatMessage
from app.schemas.human_review import HumanDecision
from app.schemas.report import EvaluationReport


class _NotAllowlistedModel(BaseModel):
    value: str


def _round_trip(serde, obj):
    type_, payload = serde.dumps_typed(obj)
    return serde.loads_typed((type_, payload))


def test_all_agentgate_state_pydantic_types_are_allowlisted():
    expected = {ChatMessage, HumanDecision, EvaluationReport}
    assert expected.issubset(set(CHECKPOINT_ALLOWED_TYPES))


def test_allowlisted_type_round_trips_without_warning(caplog):
    serde = _checkpoint_serde()
    original = ChatMessage(role="assistant", content="hello")
    restored = _round_trip(serde, original)
    assert restored == original
    assert not any("unregistered type" in r.message for r in caplog.records)


def test_human_decision_and_report_round_trip():
    """The exact two types reported unregistered before this fix."""
    from datetime import datetime

    serde = _checkpoint_serde()

    decision = HumanDecision(
        id="d1", review_request_id="r1", reviewer="alice", decision="approve",
        justification="looks good", decided_at=datetime.now(UTC),
    )
    assert _round_trip(serde, decision) == decision

    report = EvaluationReport(
        run_id="run-1", change_summary="s", risk_assessment_summary="r",
        coverage_summary="c", scenarios_passed=1, scenarios_failed=0,
        findings_summary=[], guardrails_summary=[], human_decisions_summary=[],
        infrastructure_issues_summary=[], semantic_coverage_degraded=False,
        recommendation="APPROVE", recommendation_rationale="clean run",
    )
    assert _round_trip(serde, report) == report


def test_type_outside_the_allowlist_is_blocked_not_silently_permitted(caplog):
    """An explicit allowlist is a real security boundary: a type outside it is
    blocked from reconstruction (falls back to a plain dict) and logged, rather
    than being silently instantiated like the pre-fix "allow everything with a
    warning" default did.
    """
    import logging

    serde = _checkpoint_serde()
    original = _NotAllowlistedModel(value="x")
    with caplog.at_level(logging.WARNING, logger="langgraph.checkpoint.serde.jsonplus"):
        restored = _round_trip(serde, original)
    assert restored == {"value": "x"}
    assert any("Blocked deserialization" in r.message for r in caplog.records)
