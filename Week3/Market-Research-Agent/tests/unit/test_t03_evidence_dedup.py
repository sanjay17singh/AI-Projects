"""T03 (+): same canonical URL with different tracking params dedupes to one
evidence row."""

import uuid

from app.services.evidence_service import record_evidence


def test_same_canonical_url_with_different_tracking_params_dedupes(db_session):
    run_id = uuid.uuid4()
    competitor_id = uuid.uuid4()

    id1, is_new1, needs_embed1 = record_evidence(
        db_session,
        run_id,
        competitor_id,
        "web",
        "https://example.com/pricing?utm_source=a",
        "pricing",
        "acme pricing",
        "Pricing starts at $29/mo.",
    )
    id2, is_new2, needs_embed2 = record_evidence(
        db_session,
        run_id,
        competitor_id,
        "web",
        "https://example.com/pricing?utm_source=b&utm_campaign=x",
        "pricing",
        "acme pricing",
        "Pricing starts at $29/mo.",
    )

    assert id1 == id2
    assert is_new1 is True
    assert is_new2 is False
    assert needs_embed2 is False
