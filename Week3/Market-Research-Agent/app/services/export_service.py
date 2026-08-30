"""Assembles the final Briefing from persisted CompetitorProfile rows and
orchestrates the three export formats. No LLM calls — see
export/markdown_exporter.py's docstring for why that matters.

This is also the only place that resolves an evidence_id (an internal
research_evidence.id) back into a real url/title — the exporters and the
Streamlit page never touch the DB themselves, they just receive this lookup
as plain data (see app/export/citations.py)."""

from datetime import UTC, datetime
from itertools import groupby
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Briefing as BriefingRow
from app.db.models import CompetitorProfile as CompetitorProfileRow
from app.db.models import ResearchEvidence, Run
from app.export.csv_exporter import build_csv
from app.export.markdown_exporter import build_markdown
from app.export.pdf_exporter import build_pdf
from app.schemas.analysis import CompetitorProfile
from app.schemas.briefing import Briefing, CoverageSummary, UnresolvedConflict
from app.schemas.common import ALL_PROFILE_CATEGORIES


def load_profiles(db: Session, run_id: UUID) -> list[CompetitorProfile]:
    rows = list(
        db.execute(
            select(CompetitorProfileRow).where(CompetitorProfileRow.run_id == run_id)
        ).scalars()
    )
    return [CompetitorProfile.model_validate(row.raw_profile_json) for row in rows]


def _collect_evidence_ids(profiles: list[CompetitorProfile]) -> set[str]:
    evidence_ids: set[str] = set()
    for profile in profiles:
        for category in ALL_PROFILE_CATEGORIES:
            for claim in getattr(profile, category):
                evidence_ids.update(claim.evidence_ids)
    return evidence_ids


def load_evidence_lookup(db: Session, evidence_ids: set[str]) -> dict[str, dict]:
    """Resolves evidence_ids (as they appear in ClaimField.evidence_ids —
    strings) to their real {url, title} from research_evidence. Missing IDs
    are simply absent from the returned dict; callers fall back gracefully
    (see app/export/citations.py)."""
    if not evidence_ids:
        return {}
    try:
        uuids = [UUID(eid) for eid in evidence_ids]
    except ValueError:
        return {}
    rows = db.execute(select(ResearchEvidence).where(ResearchEvidence.id.in_(uuids))).scalars()
    return {str(row.id): {"url": row.url, "title": row.title or row.canonical_url} for row in rows}


def compute_coverage_summary(profiles: list[CompetitorProfile]) -> CoverageSummary:
    sources_cited = set()
    for profile in profiles:
        for category in ALL_PROFILE_CATEGORIES:
            for claim in getattr(profile, category):
                sources_cited.update(claim.evidence_ids)

    if not profiles:
        avg_coverage = 0.0
    else:
        avg_coverage = sum(p.evidence_coverage_score for p in profiles) / len(profiles)

    if avg_coverage >= 0.7:
        label = "high"
    elif avg_coverage >= 0.4:
        label = "medium"
    else:
        label = "low"

    return CoverageSummary(
        competitors_profiled=len(profiles),
        sources_cited=len(sources_cited),
        overall_coverage_label=label,
    )


def find_unresolved_conflicts(profiles: list[CompetitorProfile]) -> list[UnresolvedConflict]:
    conflicts = []
    for profile in profiles:
        for category in ALL_PROFILE_CATEGORIES:
            claims = [c for c in getattr(profile, category) if c.conflicting_group_id]
            claims.sort(key=lambda c: c.conflicting_group_id or "")
            for _group_id, group in groupby(claims, key=lambda c: c.conflicting_group_id):
                values = [c.value for c in group]
                conflicts.append(
                    UnresolvedConflict(
                        competitor_name=profile.competitor_name, field_name=category, values=values
                    )
                )
    return conflicts


def compile_and_persist_briefing(db: Session, run_id: UUID) -> Briefing:
    run = db.get(Run, run_id)
    profiles = load_profiles(db, run_id)
    evidence_lookup = load_evidence_lookup(db, _collect_evidence_ids(profiles))

    markdown_content = build_markdown(run.target_company_name, profiles, evidence_lookup)
    coverage_summary = compute_coverage_summary(profiles)
    unresolved_conflicts = find_unresolved_conflicts(profiles)
    generated_at = datetime.now(UTC)

    row = BriefingRow(
        run_id=run_id,
        markdown_content=markdown_content,
        coverage_summary=coverage_summary.model_dump(mode="json"),
        unresolved_conflicts=[c.model_dump(mode="json") for c in unresolved_conflicts],
    )
    db.add(row)
    db.commit()

    return Briefing(
        run_id=run_id,
        target_company_name=run.target_company_name,
        generated_at=generated_at,
        coverage_summary=coverage_summary,
        profiles=profiles,
        unresolved_conflicts=unresolved_conflicts,
        markdown_content=markdown_content,
        evidence_sources=evidence_lookup,
    )


def get_briefing(db: Session, run_id: UUID) -> Briefing | None:
    row = db.execute(select(BriefingRow).where(BriefingRow.run_id == run_id)).scalar_one_or_none()
    if row is None:
        return None
    run = db.get(Run, run_id)
    profiles = load_profiles(db, run_id)
    evidence_lookup = load_evidence_lookup(db, _collect_evidence_ids(profiles))
    return Briefing(
        run_id=run_id,
        target_company_name=run.target_company_name,
        generated_at=row.generated_at,
        coverage_summary=CoverageSummary.model_validate(row.coverage_summary),
        profiles=profiles,
        unresolved_conflicts=[
            UnresolvedConflict.model_validate(c) for c in row.unresolved_conflicts
        ],
        markdown_content=row.markdown_content,
        evidence_sources=evidence_lookup,
    )


def export_csv_bytes(db: Session, run_id: UUID) -> str:
    profiles = load_profiles(db, run_id)
    evidence_lookup = load_evidence_lookup(db, _collect_evidence_ids(profiles))
    return build_csv(profiles, evidence_lookup)


def export_pdf_bytes(db: Session, run_id: UUID) -> bytes:
    run = db.get(Run, run_id)
    profiles = load_profiles(db, run_id)
    evidence_lookup = load_evidence_lookup(db, _collect_evidence_ids(profiles))
    return build_pdf(run.target_company_name, profiles, evidence_lookup)
