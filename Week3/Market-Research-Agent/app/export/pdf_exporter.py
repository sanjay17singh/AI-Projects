import io
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.export.citations import CitationIndex, build_citation_index
from app.export.markdown_exporter import CATEGORY_LABELS
from app.schemas.analysis import ClaimField, CompetitorProfile
from app.schemas.common import ALL_PROFILE_CATEGORIES


def _claim_text(claim: ClaimField, citations: CitationIndex) -> str:
    if claim.is_unsupported:
        return "<i>Not publicly available.</i>"
    markers = " ".join(citations.marker_for(eid) for eid in claim.evidence_ids)
    inference = " <i>(inference)</i>" if claim.is_inference else ""
    return (
        f"{escape(claim.value)}{inference} &mdash; confidence: {claim.confidence.value} {markers}"
    )


def _evidence_id_sequences(profile: CompetitorProfile):
    for category in ALL_PROFILE_CATEGORIES:
        for claim in getattr(profile, category):
            yield claim.evidence_ids


def build_pdf(
    target_company_name: str, profiles: list[CompetitorProfile], evidence_lookup: dict[str, dict]
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter, topMargin=0.75 * inch, bottomMargin=0.75 * inch
    )
    styles = getSampleStyleSheet()
    h1 = styles["Heading1"]
    h2 = styles["Heading2"]
    h3 = ParagraphStyle("h3", parent=styles["Heading3"], spaceBefore=8, spaceAfter=2)
    body = styles["BodyText"]

    story = [
        Paragraph(f"Competitor analysis briefing: {escape(target_company_name)}", h1),
        Spacer(1, 12),
    ]

    for profile in profiles:
        citations = build_citation_index(_evidence_id_sequences(profile), evidence_lookup)

        story.append(Paragraph(escape(profile.competitor_name), h2))
        story.append(
            Paragraph(
                f"Coverage score: {profile.evidence_coverage_score:.2f} &middot; "
                f"Overall confidence: {profile.overall_confidence.value}",
                body,
            )
        )
        for category in ALL_PROFILE_CATEGORIES:
            story.append(Paragraph(CATEGORY_LABELS.get(category, category), h3))
            for claim in getattr(profile, category):
                story.append(Paragraph(f"&bull; {_claim_text(claim, citations)}", body))

        if citations.sources:
            story.append(Paragraph("Sources", h3))
            for source in citations.sources:
                label = f"{source.number}. {escape(source.title)}"
                if source.url:
                    label += f" &mdash; {escape(source.url)}"
                story.append(Paragraph(label, body))

        story.append(Spacer(1, 16))

    doc.build(story)
    return buffer.getvalue()
