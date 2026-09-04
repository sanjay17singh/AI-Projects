"""Verifies idempotent creation/decision recording against a real Postgres
instance — this is the resilience property RES-DUPDECISION-01 describes:
submitting the same human decision twice must not double-apply it.
"""

import uuid

import pytest
from sqlalchemy import select

from app.db.models import HumanDecisionModel, HumanReviewRequestModel
from app.db.repository import (
    create_evaluation_run,
    create_human_review_request,
    create_proposed_change,
    record_human_decision,
)


@pytest.fixture
def run_id(session_factory):
    with session_factory.session() as session:
        change = create_proposed_change(
            session,
            tenant_id="default",
            change_type="prompt",
            title="test change",
            diff_summary="test",
            raw_payload={},
            created_by="tester",
        )
        run = create_evaluation_run(
            session, change_id=change.id, scenario_budget=40, idempotency_key=f"run-{uuid.uuid4()}"
        )
        session.commit()
        return run.id


def test_duplicate_evaluation_run_creation_is_idempotent(session_factory):
    key = f"idem-{uuid.uuid4()}"
    with session_factory.session() as session:
        change = create_proposed_change(
            session, tenant_id="default", change_type="prompt", title="t", diff_summary="d", raw_payload={}, created_by="tester"
        )
        session.commit()
        run1 = create_evaluation_run(session, change_id=change.id, scenario_budget=40, idempotency_key=key)
        run2 = create_evaluation_run(session, change_id=change.id, scenario_budget=40, idempotency_key=key)
        session.commit()
        assert run1.id == run2.id


def test_duplicate_human_review_request_creation_is_idempotent(session_factory, run_id):
    key = f"review-{uuid.uuid4()}"
    with session_factory.session() as session:
        review1, created1 = create_human_review_request(
            session, run_id=run_id, review_type="guardrail", evidence_ref="f1", available_actions=["approve", "reject"], idempotency_key=key
        )
        review2, created2 = create_human_review_request(
            session, run_id=run_id, review_type="guardrail", evidence_ref="f1", available_actions=["approve", "reject"], idempotency_key=key
        )
        session.commit()
        assert review1.id == review2.id
        assert created1 is True
        assert created2 is False


def test_duplicate_human_decision_does_not_double_apply(session_factory, run_id):
    with session_factory.session() as session:
        review, _ = create_human_review_request(
            session, run_id=run_id, review_type="guardrail", evidence_ref="f1", available_actions=["approve", "reject"], idempotency_key=f"review-{uuid.uuid4()}"
        )
        session.commit()
        review_id = review.id

    decision_key = f"decision-{uuid.uuid4()}"
    with session_factory.session() as session:
        d1, created1 = record_human_decision(
            session, review_request_id=review_id, reviewer="alice", decision="approve", justification="looks good", idempotency_key=decision_key
        )
        session.commit()

    with session_factory.session() as session:
        d2, created2 = record_human_decision(
            session, review_request_id=review_id, reviewer="alice", decision="approve", justification="looks good", idempotency_key=decision_key
        )
        session.commit()

    assert d1.id == d2.id
    assert created1 is True
    assert created2 is False

    with session_factory.session() as session:
        all_decisions = session.scalars(
            select(HumanDecisionModel).where(HumanDecisionModel.review_request_id == review_id)
        ).all()
        assert len(all_decisions) == 1

        review_row = session.get(HumanReviewRequestModel, review_id)
        assert review_row.status == "decided"


def test_second_decision_with_different_key_on_same_review_is_rejected_as_duplicate(session_factory, run_id):
    """Even without a matching idempotency key, a second *distinct* decision on an
    already-decided review must not create a second row — one decision per review request.
    """
    with session_factory.session() as session:
        review, _ = create_human_review_request(
            session, run_id=run_id, review_type="release", evidence_ref="run", available_actions=["approve", "reject"], idempotency_key=f"review-{uuid.uuid4()}"
        )
        session.commit()
        review_id = review.id

    with session_factory.session() as session:
        record_human_decision(
            session, review_request_id=review_id, reviewer="alice", decision="approve", justification="first", idempotency_key=f"key-{uuid.uuid4()}"
        )
        session.commit()

    with session_factory.session() as session:
        second, created = record_human_decision(
            session, review_request_id=review_id, reviewer="bob", decision="reject", justification="second, should not apply", idempotency_key=f"key-{uuid.uuid4()}"
        )
        session.commit()
        assert created is False
        assert second.reviewer == "alice"  # the original decision, not bob's
