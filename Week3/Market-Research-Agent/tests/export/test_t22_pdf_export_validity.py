"""T22 (+): PDF export produces valid, parseable PDF bytes, with a resolved
Sources section rather than raw evidence_id UUIDs."""

import io

from pypdf import PdfReader

from app.export.pdf_exporter import build_pdf
from app.schemas.analysis import ClaimField, CompetitorProfile
from app.schemas.common import Confidence


def test_pdf_export_produces_valid_parseable_pdf():
    profile = CompetitorProfile(
        competitor_id="c1",
        competitor_name="Pipeline Harbor",
        pricing=[ClaimField(value="$29/mo", evidence_ids=["e1"], confidence=Confidence.MEDIUM)],
        evidence_coverage_score=0.14,
        overall_confidence=Confidence.MEDIUM,
    )
    evidence_lookup = {"e1": {"url": "https://pipelineharbor.com/pricing", "title": "Pricing page"}}

    pdf_bytes = build_pdf("Brightleaf CRM", [profile], evidence_lookup)

    assert pdf_bytes.startswith(b"%PDF-")
    reader = PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) >= 1
    text = reader.pages[0].extract_text()
    assert "Pipeline Harbor" in text
    assert "Pricing page" in text
    assert "pipelineharbor.com/pricing" in text
