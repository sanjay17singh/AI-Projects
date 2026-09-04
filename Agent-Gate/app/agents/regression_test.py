"""Regression Test Agent: converts confirmed, now-mitigated failures into permanent tests.

Only reached (per the graph) after a guardrail was approved and the
re-execution + re-evaluation came back clean, so every finding processed
here has already been verified fixed. Deduplication is a content hash of the
derived scenario definition, so re-running this node for the same
finding/scenario never creates a second regression test.

Findings whose originating scenario carries critical/high risk are flagged
for the "regression_promotion" human-review type (per HITL requirements) —
this promotion is tracked out-of-band in the Human Review queue and does not
block the current run from completing.
"""

from app.db.models import FindingModel
from app.db.repository import create_human_review_request, create_regression_test
from app.dependencies import AgentDeps
from app.schemas.state import AgentGateState
from scenarios.catalog import get_scenario

SENSITIVE_SEVERITIES = {"high", "critical"}


def run(state: AgentGateState, deps: AgentDeps) -> dict:
    approved_finding_ids = {
        g.finding_id for g in state.get("guardrail_recommendations", []) if g.status == "approved"
    }
    findings_by_id = {f.id: f for f in state.get("findings", [])}

    regression_test_ids: list[str] = []
    mitigated_findings = []

    with deps.session_factory.session() as session:
        for finding_id in approved_finding_ids:
            finding = findings_by_id.get(finding_id)
            if finding is None:
                continue
            scenario = get_scenario(finding.scenario_id)
            scenario_definition = scenario.model_dump()

            row, created = create_regression_test(
                session,
                origin_finding_id=finding.id,
                origin_run_id=finding.run_id,
                scenario_definition=scenario_definition,
                approval_status="pending_promotion_review" if scenario.risk_level in SENSITIVE_SEVERITIES else "auto_approved",
            )
            regression_test_ids.append(row.id)

            if created:
                finding_row = session.get(FindingModel, finding.id)
                if finding_row is not None:
                    finding_row.status = "mitigated"
                mitigated_findings.append(finding.model_copy(update={"status": "mitigated"}))

                if scenario.risk_level in SENSITIVE_SEVERITIES:
                    _review, _created = create_human_review_request(
                        session,
                        run_id=state["run_id"],
                        review_type="regression_promotion",
                        evidence_ref=row.id,
                        available_actions=["approve", "reject"],
                        idempotency_key=f"regression_promotion:{row.id}",
                    )
        session.commit()

    return {"regression_test_ids": regression_test_ids, "findings": mitigated_findings}
