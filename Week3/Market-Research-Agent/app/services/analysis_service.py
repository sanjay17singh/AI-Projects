"""Deterministic scoring + persistence for competitor profiles. Nothing here
calls an LLM — evidence_coverage_score in particular must stay a pure
function of the data, since it drives graphs/edges.py's coverage-check edge."""

from itertools import groupby
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import AnalysisClaim
from app.db.models import CompetitorProfile as CompetitorProfileRow
from app.schemas.analysis import (
    ClaimField,
    CompetitorProfile,
    Conflict,
    ConflictingValue,
    ExtractedProfile,
    RedFlag,
    unsupported_claim,
)
from app.schemas.common import ALL_PROFILE_CATEGORIES, COVERAGE_CATEGORIES, Confidence

_CONFIDENCE_WEIGHT = {Confidence.HIGH: 3, Confidence.MEDIUM: 2, Confidence.LOW: 1}


def sanitize_claims(claims: list[ClaimField], valid_evidence_ids: set[str]) -> list[ClaimField]:
    """Defensive check: drop any claim citing an evidence_id that wasn't
    actually part of the retrieved set (catches a model that hallucinates a
    citation), replacing it with an explicit unsupported placeholder."""
    sanitized: list[ClaimField] = []
    for claim in claims:
        if claim.is_unsupported:
            sanitized.append(claim)
            continue
        if all(eid in valid_evidence_ids for eid in claim.evidence_ids):
            sanitized.append(claim)
        else:
            sanitized.append(unsupported_claim())
    return sanitized or [unsupported_claim()]


def sanitize_red_flags(red_flags: list[RedFlag], valid_evidence_ids: set[str]) -> list[RedFlag]:
    """Same defensive purpose as sanitize_claims: a red flag citing an
    evidence_id outside the retrieved set is dropped entirely rather than
    kept with a hallucinated citation — there is no 'unsupported red flag'
    placeholder, since an unsupported one simply shouldn't have been
    reported (see rule 6 in analysis_prompts.EXTRACTION_SYSTEM_PROMPT)."""
    sanitized: list[RedFlag] = []
    for flag in red_flags:
        if flag.evidence_ids and all(eid in valid_evidence_ids for eid in flag.evidence_ids):
            if flag.red_flag_id is None:
                flag = flag.model_copy(update={"red_flag_id": f"RF-{uuid4().hex[:12]}"})
            sanitized.append(flag)
    return sanitized


def build_conflicts(profile: CompetitorProfile) -> list[Conflict]:
    """Deterministic, Python-only aggregation of the `conflicting_group_id`
    clusters the extraction LLM already produced (rule 4 in
    analysis_prompts.EXTRACTION_SYSTEM_PROMPT) into one Conflict per group,
    across every category. Never calls an LLM — resolution_status/
    preferred_value/resolution_reason are copied from whatever the model set
    on the group's members, not re-derived here."""
    conflicts: list[Conflict] = []
    for category in ALL_PROFILE_CATEGORIES:
        claims = [c for c in getattr(profile, category) if c.conflicting_group_id]
        claims.sort(key=lambda c: c.conflicting_group_id or "")
        for _group_id, group_iter in groupby(claims, key=lambda c: c.conflicting_group_id):
            group = list(group_iter)
            resolution_status = next(
                (c.resolution_status for c in group if c.resolution_status), "unresolved"
            )
            preferred = next((c for c in group if c.is_preferred), None)
            resolution_reason = next(
                (c.resolution_reason for c in group if c.resolution_reason), None
            )
            conflicts.append(
                Conflict(
                    field=category,
                    values=[
                        ConflictingValue(value=c.value, evidence_ids=c.evidence_ids) for c in group
                    ],
                    resolution_status=resolution_status,
                    preferred_value=preferred.value if preferred else None,
                    resolution_reason=resolution_reason,
                )
            )
    return conflicts


def compute_coverage_score(extracted: ExtractedProfile) -> float:
    """(# of the COVERAGE_CATEGORIES with >=1 evidence-backed, non-unsupported
    field) / len(COVERAGE_CATEGORIES) — deterministic, never LLM-reported."""
    covered = 0
    for category in COVERAGE_CATEGORIES:
        claims: list[ClaimField] = getattr(extracted, category)
        if any(not c.is_unsupported for c in claims):
            covered += 1
    return round(covered / len(COVERAGE_CATEGORIES), 3)


def compute_overall_confidence(extracted: ExtractedProfile) -> Confidence:
    """Deterministic aggregate: weighted-average confidence across every
    evidence-backed claim in COVERAGE_CATEGORIES."""
    weights = []
    for category in COVERAGE_CATEGORIES:
        for claim in getattr(extracted, category):
            if not claim.is_unsupported:
                weights.append(_CONFIDENCE_WEIGHT[claim.confidence])
    if not weights:
        return Confidence.LOW
    avg = sum(weights) / len(weights)
    if avg >= 2.5:
        return Confidence.HIGH
    if avg >= 1.5:
        return Confidence.MEDIUM
    return Confidence.LOW


def assemble_competitor_profile(
    competitor_id: str, competitor_name: str, extracted: ExtractedProfile
) -> CompetitorProfile:
    return CompetitorProfile(
        competitor_id=competitor_id,
        competitor_name=competitor_name,
        evidence_coverage_score=compute_coverage_score(extracted),
        overall_confidence=compute_overall_confidence(extracted),
        red_flags=extracted.red_flags,
        **{category: getattr(extracted, category) for category in ALL_PROFILE_CATEGORIES},
    )


def persist_profile(
    db: Session, run_id: UUID, competitor_id: UUID, profile: CompetitorProfile
) -> UUID:
    row = CompetitorProfileRow(
        run_id=run_id,
        competitor_id=competitor_id,
        evidence_coverage_score=profile.evidence_coverage_score,
        overall_confidence=profile.overall_confidence.value,
        raw_profile_json=profile.model_dump(mode="json"),
    )
    db.add(row)
    db.flush()

    for category in ALL_PROFILE_CATEGORIES:
        for claim in getattr(profile, category):
            db.add(
                AnalysisClaim(
                    competitor_profile_id=row.id,
                    category=category,
                    field_name=category,
                    value_text=claim.value,
                    is_inference=claim.is_inference,
                    confidence=claim.confidence.value,
                    evidence_ids=claim.evidence_ids,
                    is_unsupported=claim.is_unsupported,
                    conflicting_group_id=claim.conflicting_group_id,
                    source_dates=claim.source_dates,
                )
            )
    db.commit()
    db.refresh(row)
    return row.id


def upsert_profile(
    db: Session, run_id: UUID, competitor_id: UUID, profile: CompetitorProfile
) -> UUID:
    """Used by gap_research_node, which re-runs analysis after fetching more
    evidence — replaces the prior profile+claims rather than trying to merge
    them field-by-field."""
    existing = db.execute(
        select(CompetitorProfileRow).where(
            CompetitorProfileRow.run_id == run_id,
            CompetitorProfileRow.competitor_id == competitor_id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        db.execute(delete(AnalysisClaim).where(AnalysisClaim.competitor_profile_id == existing.id))
        db.delete(existing)
        db.flush()
    return persist_profile(db, run_id, competitor_id, profile)
