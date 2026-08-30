"""T21 (+): CSV export has one row per claim with the expected columns, and
the "sources" column resolves to real URLs rather than raw evidence_id
UUIDs."""

import csv
import io

from app.export.csv_exporter import build_csv
from app.schemas.analysis import ClaimField, CompetitorProfile
from app.schemas.common import ALL_PROFILE_CATEGORIES, Confidence


def test_csv_has_one_row_per_claim_with_expected_columns():
    profile = CompetitorProfile(
        competitor_id="c1",
        competitor_name="Pipeline Harbor",
        pricing=[ClaimField(value="$29/mo", evidence_ids=["e1"], confidence=Confidence.MEDIUM)],
        core_features=[ClaimField(value="CRM", evidence_ids=["e2"], confidence=Confidence.MEDIUM)],
        evidence_coverage_score=0.29,
        overall_confidence=Confidence.MEDIUM,
    )
    evidence_lookup = {"e1": {"url": "https://pipelineharbor.com/pricing", "title": "Pricing"}}

    csv_text = build_csv([profile], evidence_lookup)
    rows = list(csv.DictReader(io.StringIO(csv_text)))

    assert set(rows[0].keys()) == {
        "competitor",
        "category",
        "field",
        "value",
        "confidence",
        "sources",
    }
    # exactly one row per claim across all categories (unsupported + the 2 real ones)
    assert len(rows) == len(ALL_PROFILE_CATEGORIES)

    pricing_row = next(r for r in rows if r["category"] == "pricing")
    assert pricing_row["value"] == "$29/mo"
    assert pricing_row["sources"] == "https://pipelineharbor.com/pricing"

    # e2 has no lookup entry — falls back to the raw evidence_id rather than
    # silently dropping it or raising.
    features_row = next(r for r in rows if r["category"] == "core_features")
    assert features_row["sources"] == "e2"
