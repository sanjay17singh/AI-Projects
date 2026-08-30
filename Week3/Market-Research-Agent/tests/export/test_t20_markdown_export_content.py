"""T20 (+): Markdown export contains competitor headers, confidence labels,
and cited evidence (resolved to a numbered footnote + a real source) for
each claim."""

from app.export.markdown_exporter import build_markdown
from app.schemas.analysis import ClaimField, CompetitorProfile
from app.schemas.common import Confidence


def test_markdown_contains_headers_confidence_and_citations():
    profile = CompetitorProfile(
        competitor_id="c1",
        competitor_name="Pipeline Harbor",
        pricing=[
            ClaimField(
                value="$29-$99/mo", evidence_ids=["evid-1", "evid-2"], confidence=Confidence.HIGH
            )
        ],
        evidence_coverage_score=0.14,
        overall_confidence=Confidence.MEDIUM,
    )
    evidence_lookup = {
        "evid-1": {"url": "https://pipelineharbor.com/pricing", "title": "Pipeline Harbor pricing"},
        "evid-2": {"url": "https://g2.com/pipeline-harbor", "title": "Pipeline Harbor on G2"},
    }

    markdown = build_markdown("Brightleaf CRM", [profile], evidence_lookup)

    assert "# Competitor analysis briefing: Brightleaf CRM" in markdown
    assert "## Pipeline Harbor" in markdown
    assert "confidence: high" in markdown
    assert "[1]" in markdown and "[2]" in markdown
    assert "1. Pipeline Harbor pricing — https://pipelineharbor.com/pricing" in markdown
    assert "2. Pipeline Harbor on G2 — https://g2.com/pipeline-harbor" in markdown
