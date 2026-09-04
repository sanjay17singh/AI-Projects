"""Verifies the fail-closed guarantee: if persisting the human_review_request
or its audit event fails, request_human_review raises FailClosedError instead
of proceeding to interrupt() on unpersisted state.
"""

import pytest

from app.agents.orchestrator import FailClosedError, request_human_review


class _BrokenSessionFactory:
    def session(self):
        raise RuntimeError("simulated Postgres outage")


class _FakeDeps:
    def __init__(self, session_factory):
        self.session_factory = session_factory


def test_request_human_review_fails_closed_on_db_outage():
    state = {"run_id": "run-1", "correlation_id": "corr-1"}
    deps = _FakeDeps(_BrokenSessionFactory())

    with pytest.raises(FailClosedError):
        request_human_review(
            state,
            deps,
            review_type="budget",
            evidence_ref="budget:run-1",
            available_actions=["approve", "reject"],
            idempotency_key="budget:run-1",
        )
