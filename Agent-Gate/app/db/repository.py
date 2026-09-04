"""Persistence layer — the authoritative writes behind every agent action.

Every creation function is idempotent on its `idempotency_key`: calling it
twice with the same key returns the original row instead of creating a
duplicate. This is what lets the graph safely resume after a crash without
double-applying a human decision, a guardrail, or a regression test.
"""

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.redaction import redact_value
from app.db.models import (
    EvaluationRunModel,
    EvidenceModel,
    FindingModel,
    GuardrailRecommendationModel,
    HumanDecisionModel,
    HumanReviewRequestModel,
    ProposedChangeModel,
    RegressionTestModel,
    ReleaseDecisionModel,
    ScenarioExecutionModel,
)


def get_run(session: Session, run_id: str) -> EvaluationRunModel | None:
    return session.get(EvaluationRunModel, run_id)


def list_runs_with_change(session: Session, limit: int = 50) -> list[tuple[EvaluationRunModel, ProposedChangeModel]]:
    rows = session.execute(
        select(EvaluationRunModel, ProposedChangeModel)
        .join(ProposedChangeModel, EvaluationRunModel.change_id == ProposedChangeModel.id)
        .order_by(EvaluationRunModel.created_at.desc())
        .limit(limit)
    ).all()
    return [(row[0], row[1]) for row in rows]


def get_review_request(session: Session, review_id: str) -> HumanReviewRequestModel | None:
    return session.get(HumanReviewRequestModel, review_id)


def list_pending_reviews(session: Session) -> list[HumanReviewRequestModel]:
    return list(
        session.scalars(select(HumanReviewRequestModel).where(HumanReviewRequestModel.status == "pending")).all()
    )


def list_scenario_executions(session: Session, run_id: str) -> list[ScenarioExecutionModel]:
    return list(session.scalars(select(ScenarioExecutionModel).where(ScenarioExecutionModel.run_id == run_id)).all())


def list_findings(session: Session, run_id: str) -> list[FindingModel]:
    return list(session.scalars(select(FindingModel).where(FindingModel.run_id == run_id)).all())


class DuplicateDecisionError(Exception):
    """A decision already exists for this review request under a different key/value."""


def create_proposed_change(session: Session, *, tenant_id, change_type, title, diff_summary, raw_payload, created_by) -> ProposedChangeModel:
    change = ProposedChangeModel(
        tenant_id=tenant_id,
        change_type=change_type,
        title=title,
        diff_summary=diff_summary,
        raw_payload=raw_payload,
        created_by=created_by,
    )
    session.add(change)
    session.flush()
    return change


def create_evaluation_run(
    session: Session, *, change_id: str, scenario_budget: int, idempotency_key: str
) -> EvaluationRunModel:
    existing = session.scalar(select(EvaluationRunModel).where(EvaluationRunModel.idempotency_key == idempotency_key))
    if existing:
        return existing
    run = EvaluationRunModel(change_id=change_id, scenario_budget=scenario_budget, idempotency_key=idempotency_key)
    session.add(run)
    session.flush()
    return run


def update_run_status(session: Session, run_id: str, **fields) -> None:
    run = session.get(EvaluationRunModel, run_id)
    if run is None:
        raise ValueError(f"unknown run_id: {run_id}")
    for key, value in fields.items():
        setattr(run, key, value)
    session.flush()


def record_scenario_execution(
    session: Session,
    *,
    run_id: str,
    scenario_id: str,
    attempt: int,
    target_config: str,
    status: str,
    transcript: list[dict],
    tool_calls: list[dict],
    final_output: str,
    latency_ms: float,
    error: str | None,
) -> ScenarioExecutionModel:
    idempotency_key = f"{run_id}:{scenario_id}:{attempt}"
    existing = session.scalar(
        select(ScenarioExecutionModel).where(ScenarioExecutionModel.idempotency_key == idempotency_key)
    )
    if existing:
        return existing
    execution = ScenarioExecutionModel(
        run_id=run_id,
        scenario_id=scenario_id,
        attempt=attempt,
        target_config=target_config,
        status=status,
        transcript=redact_value(transcript),
        tool_calls=redact_value(tool_calls),
        final_output=redact_value(final_output),
        latency_ms=latency_ms,
        error=error,
        idempotency_key=idempotency_key,
    )
    session.add(execution)
    session.flush()
    return execution


def record_finding(
    session: Session,
    *,
    run_id: str,
    scenario_execution_id: str,
    scenario_id: str,
    severity: str,
    category: str,
    assertion_source: str,
    description: str,
) -> FindingModel:
    finding = FindingModel(
        run_id=run_id,
        scenario_execution_id=scenario_execution_id,
        scenario_id=scenario_id,
        severity=severity,
        category=category,
        assertion_source=assertion_source,
        description=description,
    )
    session.add(finding)
    session.flush()
    return finding


def record_evidence(
    session: Session,
    *,
    finding_id: str | None,
    scenario_execution_id: str | None,
    evidence_type: str,
    content: dict,
) -> EvidenceModel:
    redacted = redact_value(content)
    content_hash = hashlib.sha256(json.dumps(redacted, sort_keys=True, default=str).encode()).hexdigest()
    evidence = EvidenceModel(
        finding_id=finding_id,
        scenario_execution_id=scenario_execution_id,
        evidence_type=evidence_type,
        redacted_content=redacted,
        content_hash=content_hash,
    )
    session.add(evidence)
    session.flush()
    return evidence


def create_guardrail_recommendation(
    session: Session,
    *,
    run_id: str,
    finding_id: str,
    failure_summary: str,
    proposed_change: str,
    benefit: str,
    side_effects: str,
    validation_scenarios: list[str],
    rollback_guidance: str,
) -> GuardrailRecommendationModel:
    guardrail = GuardrailRecommendationModel(
        run_id=run_id,
        finding_id=finding_id,
        failure_summary=failure_summary,
        proposed_change=proposed_change,
        benefit=benefit,
        side_effects=side_effects,
        validation_scenarios=validation_scenarios,
        rollback_guidance=rollback_guidance,
    )
    session.add(guardrail)
    session.flush()
    return guardrail


def update_guardrail_status(session: Session, guardrail_id: str, status: str) -> None:
    guardrail = session.get(GuardrailRecommendationModel, guardrail_id)
    if guardrail is None:
        raise ValueError(f"unknown guardrail_id: {guardrail_id}")
    guardrail.status = status
    session.flush()


def create_human_review_request(
    session: Session,
    *,
    run_id: str,
    review_type: str,
    evidence_ref: str,
    available_actions: list[str],
    idempotency_key: str,
) -> tuple[HumanReviewRequestModel, bool]:
    existing = session.scalar(
        select(HumanReviewRequestModel).where(HumanReviewRequestModel.idempotency_key == idempotency_key)
    )
    if existing:
        return existing, False
    review = HumanReviewRequestModel(
        run_id=run_id,
        review_type=review_type,
        evidence_ref=evidence_ref,
        available_actions=available_actions,
        idempotency_key=idempotency_key,
    )
    session.add(review)
    session.flush()
    return review, True


def record_human_decision(
    session: Session,
    *,
    review_request_id: str,
    reviewer: str,
    decision: str,
    justification: str,
    idempotency_key: str,
) -> tuple[HumanDecisionModel, bool]:
    """Returns (decision_row, created). If a decision already exists for this
    review request, returns the existing row with created=False — this is the
    idempotent-duplicate-decision path, not an error.
    """
    if not justification.strip():
        raise ValueError("justification is required for every human decision")

    existing_by_key = session.scalar(
        select(HumanDecisionModel).where(HumanDecisionModel.idempotency_key == idempotency_key)
    )
    if existing_by_key:
        return existing_by_key, False

    existing_for_request = session.scalar(
        select(HumanDecisionModel).where(HumanDecisionModel.review_request_id == review_request_id)
    )
    if existing_for_request:
        return existing_for_request, False

    row = HumanDecisionModel(
        review_request_id=review_request_id,
        reviewer=reviewer,
        decision=decision,
        justification=justification,
        idempotency_key=idempotency_key,
    )
    session.add(row)
    session.flush()

    review = session.get(HumanReviewRequestModel, review_request_id)
    if review is not None:
        review.status = "decided"

    return row, True


def create_release_decision(
    session: Session, *, run_id: str, recommendation: str, decided_by: str, idempotency_key: str
) -> tuple[ReleaseDecisionModel, bool]:
    existing = session.scalar(
        select(ReleaseDecisionModel).where(ReleaseDecisionModel.idempotency_key == idempotency_key)
    )
    if existing:
        return existing, False
    row = ReleaseDecisionModel(
        run_id=run_id, recommendation=recommendation, decided_by=decided_by, idempotency_key=idempotency_key
    )
    session.add(row)
    session.flush()
    return row, True


def create_regression_test(
    session: Session,
    *,
    origin_finding_id: str,
    origin_run_id: str,
    scenario_definition: dict,
    approval_status: str = "pending",
) -> tuple[RegressionTestModel, bool]:
    dedup_hash = hashlib.sha256(
        json.dumps(scenario_definition, sort_keys=True, default=str).encode()
    ).hexdigest()
    existing = session.scalar(select(RegressionTestModel).where(RegressionTestModel.dedup_hash == dedup_hash))
    if existing:
        return existing, False
    row = RegressionTestModel(
        origin_finding_id=origin_finding_id,
        origin_run_id=origin_run_id,
        scenario_definition=scenario_definition,
        dedup_hash=dedup_hash,
        approval_status=approval_status,
        idempotency_key=f"regression:{dedup_hash}",
    )
    session.add(row)
    session.flush()
    return row, True
