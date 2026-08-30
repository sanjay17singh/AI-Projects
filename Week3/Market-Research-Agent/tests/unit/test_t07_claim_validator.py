"""T07 (-): a claim missing evidence_ids for a non-"unavailable" value is
rejected by the Pydantic validator."""

import pytest
from pydantic import ValidationError

from app.schemas.analysis import ClaimField
from app.schemas.common import UNSUPPORTED_VALUE


def test_claim_without_evidence_ids_is_rejected():
    with pytest.raises(ValidationError):
        ClaimField(value="Starts at $29/mo", evidence_ids=[])


def test_unsupported_claim_does_not_require_evidence_ids():
    claim = ClaimField(value=UNSUPPORTED_VALUE, evidence_ids=[])
    assert claim.is_unsupported is True
