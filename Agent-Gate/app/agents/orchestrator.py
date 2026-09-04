"""Orchestrator Agent.

Owns every workflow transition in the graph and the entire human-in-the-loop
interrupt protocol. No other agent decides where the graph goes next or
whether to pause for a human — every conditional edge in
app/graph/workflow.py calls into this module, and every interrupt point
calls request_human_review().

Fail-closed guarantee: request_human_review persists the review request and
its audit event *before* calling interrupt(). If either write fails, this
raises FailClosedError instead of pausing on unpersisted state.
"""

from typing import Literal

import structlog
from langgraph.types import interrupt

from app.audit.logger import compute_state_hash, record_audit_event
from app.db.repository import create_human_review_request, record_human_decision
from app.dependencies import AgentDeps
from app.schemas.human_review import HumanDecision
from app.schemas.state import AgentGateState

logger = structlog.get_logger(__name__)

MAX_GUARDRAIL_REENTRY = 1

SENSITIVE_CHANGE_TYPES = {"tool", "policy"}
RELEASE_ALWAYS_REQUIRES_HUMAN = True  # the Target Support Agent always touches refunds/customer data


class FailClosedError(Exception):
    """A critical persistence step failed right before a human interrupt point —
    the run must halt rather than proceed on unpersisted state."""


def request_human_review(
    state: AgentGateState,
    deps: AgentDeps,
    *,
    review_type: str,
    evidence_ref: str,
    available_actions: list[str],
    idempotency_key: str,
) -> dict:
    """Persists the review request (idempotently) and an audit event, pauses the
    graph via interrupt(), and — once resumed with a decision payload —
    persists the human decision (also idempotently) and returns the state
    update. Node code that calls this should `return` its result directly.
    """
    try:
        with deps.session_factory.session() as session:
            review_row, created = create_human_review_request(
                session,
                run_id=state["run_id"],
                review_type=review_type,
                evidence_ref=evidence_ref,
                available_actions=available_actions,
                idempotency_key=idempotency_key,
            )
            session.commit()
    except Exception as exc:
        raise FailClosedError(f"could not persist human_review_request: {exc}") from exc

    if created:
        try:
            record_audit_event(
                deps.session_factory,
                run_id=state["run_id"],
                actor="orchestrator",
                action=f"human_review_requested:{review_type}",
                correlation_id=state["correlation_id"],
                input_ref=evidence_ref,
                state_hash=compute_state_hash({k: str(v) for k, v in state.items() if k != "change"}),
                metadata={"review_id": review_row.id, "available_actions": available_actions},
            )
        except Exception as exc:
            raise FailClosedError(f"could not persist audit event: {exc}") from exc

    # Note: state["pending_human_review"] is intentionally never set to a live
    # HumanReviewRequest here — interrupt() suspends this node before any return
    # can happen, so there's no state update to attach it to while paused. What's
    # pending is surfaced via LangGraph's own `__interrupt__` result (see
    # app/api/routes/evaluations.py's _pending_review helper), which is what the
    # API/UI actually read. The field is cleared below once a decision resumes it.
    decision_payload = interrupt(
        {
            "review_id": review_row.id,
            "review_type": review_type,
            "evidence_ref": evidence_ref,
            "available_actions": available_actions,
        }
    )

    try:
        with deps.session_factory.session() as session:
            decision_row, _created = record_human_decision(
                session,
                review_request_id=review_row.id,
                reviewer=decision_payload["reviewer"],
                decision=decision_payload["decision"],
                justification=decision_payload["justification"],
                idempotency_key=decision_payload.get(
                    "idempotency_key", f"{review_row.id}:{decision_payload['reviewer']}:{decision_payload['decision']}"
                ),
            )
            session.commit()
    except Exception as exc:
        raise FailClosedError(f"could not persist human_decision: {exc}") from exc

    human_decision = HumanDecision(
        id=decision_row.id,
        review_request_id=decision_row.review_request_id,
        reviewer=decision_row.reviewer,
        decision=decision_row.decision,
        justification=decision_row.justification,
        decided_at=decision_row.decided_at,
    )
    return {"pending_human_review": None, "human_decisions": [human_decision]}


def route_after_budget_check(state: AgentGateState) -> Literal["within_budget", "needs_approval"]:
    budget = state.get("budget")
    if budget is None or not budget.exceeds_budget:
        return "within_budget"
    return "needs_approval"


def route_after_budget_review(state: AgentGateState) -> Literal["proceed", "abort"]:
    decisions = state.get("human_decisions", [])
    if decisions and decisions[-1].decision == "approve":
        return "proceed"
    return "abort"


def route_after_policy_evaluation(
    state: AgentGateState,
) -> Literal["first_pass_clean", "first_pass_findings", "reentry_clean", "reentry_findings"]:
    """The graph allows exactly MAX_GUARDRAIL_REENTRY (1) trip back through the
    guardrail-approval loop: findings found on the re-verification pass go
    straight to report_generation (as BLOCK/INCONCLUSIVE material) rather than
    looping again, which is what bounds this to a single re-entry.
    """
    all_executions = state.get("executions", [])
    latest_attempt = max((e.attempt for e in all_executions), default=1)
    findings = state.get("findings", [])
    guardrails = state.get("guardrail_recommendations", [])
    approved_ids = {g.finding_id for g in guardrails if g.status == "approved"}

    if latest_attempt > 1:
        unresolved = [f for f in findings if f.id not in approved_ids]
        return "reentry_clean" if not unresolved else "reentry_findings"

    return "first_pass_clean" if not findings else "first_pass_findings"


def route_after_guardrail_review(state: AgentGateState) -> Literal["approved", "rejected"]:
    decisions = state.get("human_decisions", [])
    if decisions and decisions[-1].decision == "approve":
        return "approved"
    return "rejected"


def release_requires_human_review(state: AgentGateState) -> bool:
    report = state.get("report")
    if report is None:
        return True
    if report.recommendation in ("BLOCK", "INCONCLUSIVE"):
        return True
    if RELEASE_ALWAYS_REQUIRES_HUMAN:
        return True
    return state["change"].change_type in SENSITIVE_CHANGE_TYPES
