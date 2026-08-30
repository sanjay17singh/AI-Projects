from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import DiscoveryCandidate
from app.schemas.discovery import CompetitorCandidate


def persist_candidates(
    db: Session, run_id: UUID, candidates: list[CompetitorCandidate]
) -> list[DiscoveryCandidate]:
    rows = []
    for rank, candidate in enumerate(candidates, start=1):
        row = DiscoveryCandidate(
            run_id=run_id,
            company_name=candidate.company_name,
            website=candidate.website,
            match_score=candidate.match_score,
            classification=candidate.classification.value,
            explanation=candidate.explanation,
            source_urls=candidate.source_urls,
            rank=rank,
        )
        db.add(row)
        rows.append(row)
    db.commit()
    for row in rows:
        db.refresh(row)
    return rows


def get_candidates(db: Session, run_id: UUID) -> list[DiscoveryCandidate]:
    return list(
        db.execute(
            select(DiscoveryCandidate)
            .where(DiscoveryCandidate.run_id == run_id)
            .order_by(DiscoveryCandidate.rank)
        ).scalars()
    )
