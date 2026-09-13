"""T27 (+): RedFlag evidence-sanitization mirrors sanitize_claims (drop, don't
hallucinate-through, a flag citing an evidence_id outside the retrieved set),
and build_conflicts derives a group-level Conflict from ClaimField groups
without ever calling an LLM."""

import pytest

from app.schemas.analysis import ClaimField, CompetitorProfile, RedFlag
from app.schemas.common import Confidence
from app.services.analysis_service import build_conflicts, sanitize_red_flags


def test_red_flag_requires_at_least_one_evidence_id():
    with pytest.raises(ValueError):
        RedFlag(
            type="security_incident", severity="critical", description="breach", evidence_ids=[]
        )


def test_sanitize_red_flags_drops_hallucinated_citation_and_assigns_id():
    flags = [
        RedFlag(type="price_increase", severity="high", description="doubled", evidence_ids=["e1"]),
        RedFlag(
            type="security_incident",
            severity="critical",
            description="breach",
            evidence_ids=["not-retrieved"],
        ),
    ]
    sanitized = sanitize_red_flags(flags, {"e1"})
    assert len(sanitized) == 1
    assert sanitized[0].type == "price_increase"
    assert sanitized[0].red_flag_id is not None


def test_build_conflicts_groups_claims_and_carries_resolution_fields():
    profile = CompetitorProfile(
        competitor_id="c1",
        competitor_name="Pipeline Harbor",
        pricing=[
            ClaimField(
                value="$99/month",
                evidence_ids=["e1"],
                confidence=Confidence.MEDIUM,
                conflicting_group_id="g1",
                resolution_status="resolved",
                is_preferred=False,
                resolution_reason="e2 is more recent",
            ),
            ClaimField(
                value="$149/month",
                evidence_ids=["e2"],
                confidence=Confidence.MEDIUM,
                conflicting_group_id="g1",
                resolution_status="resolved",
                is_preferred=True,
                resolution_reason="e2 is more recent",
            ),
        ],
        evidence_coverage_score=0.1,
        overall_confidence=Confidence.MEDIUM,
    )
    conflicts = build_conflicts(profile)
    assert len(conflicts) == 1
    conflict = conflicts[0]
    assert conflict.field == "pricing"
    assert {v.value for v in conflict.values} == {"$99/month", "$149/month"}
    assert conflict.resolution_status == "resolved"
    assert conflict.preferred_value == "$149/month"
    assert conflict.resolution_reason == "e2 is more recent"


def test_build_conflicts_defaults_to_unresolved_when_model_left_it_unset():
    profile = CompetitorProfile(
        competitor_id="c1",
        competitor_name="Pipeline Harbor",
        pricing=[
            ClaimField(value="$99/month", evidence_ids=["e1"], conflicting_group_id="g1"),
            ClaimField(value="$149/month", evidence_ids=["e2"], conflicting_group_id="g1"),
        ],
        evidence_coverage_score=0.1,
        overall_confidence=Confidence.LOW,
    )
    conflicts = build_conflicts(profile)
    assert conflicts[0].resolution_status == "unresolved"
    assert conflicts[0].preferred_value is None
