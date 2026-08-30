"""The only module that writes research_evidence rows. Handles dedup by
canonical URL + content hash so the Web Research Agent never has to touch a
DB session directly (layering rule: agents/graph nodes call services)."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ResearchEvidence
from app.utils.hashing import content_hash
from app.utils.urls import canonicalize_url


def record_evidence(
    db: Session,
    run_id: UUID,
    competitor_id: UUID,
    source_type: str,
    url: str,
    category: str,
    query_used: str,
    evidence_text: str,
    title: str | None = None,
    published_at: datetime | None = None,
    provider: str = "you_com",
) -> tuple[UUID, bool, bool]:
    """Returns (evidence_id, is_new_row, needs_embedding).

    - Exact dedupe (same canonical_url + content_hash already seen this run for
      this competitor): returns the existing row's id, needs_embedding=False.
    - Content dedupe (different canonical_url, same content_hash): inserts a
      new row with dedupe_of set, needs_embedding=False (no point re-embedding
      identical text under a second evidence_id).
    - Otherwise: inserts a fresh row, needs_embedding=True.
    """
    canonical = canonicalize_url(url)
    chash = content_hash(evidence_text)

    exact_match = db.execute(
        select(ResearchEvidence).where(
            ResearchEvidence.run_id == run_id,
            ResearchEvidence.competitor_id == competitor_id,
            ResearchEvidence.canonical_url == canonical,
            ResearchEvidence.content_hash == chash,
        )
    ).scalar_one_or_none()
    if exact_match is not None:
        return exact_match.id, False, False

    content_match = db.execute(
        select(ResearchEvidence).where(
            ResearchEvidence.run_id == run_id,
            ResearchEvidence.competitor_id == competitor_id,
            ResearchEvidence.content_hash == chash,
        )
    ).scalar_one_or_none()

    row = ResearchEvidence(
        run_id=run_id,
        competitor_id=competitor_id,
        source_type=source_type,
        url=url,
        canonical_url=canonical,
        content_hash=chash,
        title=title,
        published_at=published_at,
        fetched_at=datetime.now(UTC),
        query_used=query_used,
        provider=provider,
        raw_snippet=evidence_text[:500],
        chunk_count=0,
        embedding_status="pending",
        dedupe_of=content_match.id if content_match is not None else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    needs_embedding = content_match is None
    return row.id, True, needs_embedding


def update_embedding_status(db: Session, evidence_id: UUID, status: str, chunk_count: int) -> None:
    row = db.get(ResearchEvidence, evidence_id)
    if row is None:
        return
    row.embedding_status = status
    row.chunk_count = chunk_count
    db.commit()
