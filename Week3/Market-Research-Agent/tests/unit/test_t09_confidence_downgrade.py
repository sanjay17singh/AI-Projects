"""T09 (+): a 1-source "high" confidence claim is downgraded to "medium"."""

from app.schemas.analysis import ClaimField
from app.schemas.common import Confidence


def test_single_source_high_confidence_is_downgraded_to_medium():
    claim = ClaimField(value="Series A raised", evidence_ids=["e1"], confidence=Confidence.HIGH)
    assert claim.confidence == Confidence.MEDIUM


def test_two_source_high_confidence_is_kept():
    claim = ClaimField(
        value="Series A raised", evidence_ids=["e1", "e2"], confidence=Confidence.HIGH
    )
    assert claim.confidence == Confidence.HIGH
