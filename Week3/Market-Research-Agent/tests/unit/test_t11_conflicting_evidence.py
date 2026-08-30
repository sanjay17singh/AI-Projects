"""T11 (+): two contradictory pricing claims for the same competitor are both
preserved under one conflicting_group_id, not silently merged."""

from app.schemas.analysis import ClaimField, CompetitorProfile
from app.schemas.common import Confidence
from app.services.analysis_service import sanitize_claims
from app.services.export_service import find_unresolved_conflicts


def test_conflicting_claims_both_preserved_by_sanitize():
    claims = [
        ClaimField(
            value="Raised $8M",
            evidence_ids=["e1"],
            confidence=Confidence.MEDIUM,
            conflicting_group_id="g1",
            source_dates=["2026-06-12"],
        ),
        ClaimField(
            value="Raised $6.5M",
            evidence_ids=["e2"],
            confidence=Confidence.MEDIUM,
            conflicting_group_id="g1",
            source_dates=["2026-06-14"],
        ),
    ]
    sanitized = sanitize_claims(claims, {"e1", "e2"})
    assert len(sanitized) == 2
    assert {c.value for c in sanitized} == {"Raised $8M", "Raised $6.5M"}


def test_find_unresolved_conflicts_reports_the_group():
    profile = CompetitorProfile(
        competitor_id="c1",
        competitor_name="Pipeline Harbor",
        announcements=[
            ClaimField(
                value="Raised $8M",
                evidence_ids=["e1"],
                confidence=Confidence.MEDIUM,
                conflicting_group_id="g1",
            ),
            ClaimField(
                value="Raised $6.5M",
                evidence_ids=["e2"],
                confidence=Confidence.MEDIUM,
                conflicting_group_id="g1",
            ),
        ],
        evidence_coverage_score=0.14,
        overall_confidence=Confidence.MEDIUM,
    )
    conflicts = find_unresolved_conflicts([profile])
    assert len(conflicts) == 1
    assert conflicts[0].field_name == "announcements"
    assert set(conflicts[0].values) == {"Raised $8M", "Raised $6.5M"}
