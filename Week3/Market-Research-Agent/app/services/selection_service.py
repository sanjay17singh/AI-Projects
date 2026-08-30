"""Enforces 'exactly 3 competitors' — a Postgres CHECK constraint can't count
sibling rows, so this Python check is the actual enforcement (see plan
section 3 / test T16)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CompetitorSelection, DiscoveryCandidate

REQUIRED_SELECTION_COUNT = 3


class InvalidSelectionError(ValueError):
    pass


def validate_and_persist_selection(
    db: Session, run_id: UUID, candidate_ids: list[UUID]
) -> list[DiscoveryCandidate]:
    if len(candidate_ids) != REQUIRED_SELECTION_COUNT:
        raise InvalidSelectionError(
            f"Expected exactly {REQUIRED_SELECTION_COUNT} competitor_candidate_ids, "
            f"got {len(candidate_ids)}"
        )
    if len(set(candidate_ids)) != REQUIRED_SELECTION_COUNT:
        raise InvalidSelectionError("competitor_candidate_ids must be distinct")

    candidates = list(
        db.execute(
            select(DiscoveryCandidate).where(
                DiscoveryCandidate.run_id == run_id, DiscoveryCandidate.id.in_(candidate_ids)
            )
        ).scalars()
    )
    if len(candidates) != REQUIRED_SELECTION_COUNT:
        raise InvalidSelectionError(
            "One or more competitor_candidate_ids do not belong to this run's discovery candidates"
        )

    for candidate_id in candidate_ids:
        db.add(CompetitorSelection(run_id=run_id, discovery_candidate_id=candidate_id))
    db.commit()

    by_id = {c.id: c for c in candidates}
    return [by_id[cid] for cid in candidate_ids]
