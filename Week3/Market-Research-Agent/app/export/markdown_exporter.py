"""Pure Python templating over already-verified CompetitorProfile objects —
deliberately no LLM call anywhere in this module. That absence is what
structurally guarantees the briefing never states a fact absent from
verified agent output (plan section: 'compile_briefing... no LLM call').

Citations are footnote-style [1], [2]... per competitor, resolved against
research_evidence — see app/export/citations.py and
services/export_service.py's evidence_lookup, which is the one place that
actually queries Postgres for the real url/title behind each evidence_id."""

from itertools import groupby

from app.export.citations import CitationIndex, build_citation_index
from app.schemas.analysis import ClaimField, CompetitorProfile
from app.schemas.common import ALL_PROFILE_CATEGORIES, Classification

CATEGORY_LABELS = {
    "company_description": "Company description",
    "pricing": "Pricing",
    "core_features": "Core features",
    "target_customers": "Target customers",
    "positioning": "Positioning",
    "differentiators": "Differentiators",
    "announcements": "Recent announcements",
    "recent_news": "Recent news",
    "free_trial": "Free plan / trial",
    "customer_reviews": "Customer reviews",
    "notable_customers": "Notable customers",
}


def _render_claim_line(claim: ClaimField, citations: CitationIndex) -> str:
    if claim.is_unsupported:
        return "*Not publicly available.*"
    markers = "".join(citations.marker_for(eid) for eid in claim.evidence_ids)
    inference_tag = " _(inference)_" if claim.is_inference else ""
    return f"{claim.value}{inference_tag} — confidence: {claim.confidence.value} {markers}"


def _render_category(
    category: str, claims: list[ClaimField], citations: CitationIndex
) -> list[str]:
    lines = [f"**{CATEGORY_LABELS.get(category, category)}**"]

    conflicting = [c for c in claims if c.conflicting_group_id]
    non_conflicting = [c for c in claims if not c.conflicting_group_id]

    for claim in non_conflicting:
        lines.append(f"- {_render_claim_line(claim, citations)}")

    conflicting_sorted = sorted(conflicting, key=lambda c: c.conflicting_group_id or "")
    for _group_id, group in groupby(conflicting_sorted, key=lambda c: c.conflicting_group_id):
        group_claims = list(group)
        lines.append("- **[Conflicting evidence]** Sources disagree — both values are preserved:")
        for claim in group_claims:
            dates = f" ({', '.join(claim.source_dates)})" if claim.source_dates else ""
            markers = "".join(citations.marker_for(eid) for eid in claim.evidence_ids)
            lines.append(f"  - {claim.value}{dates} {markers}")

    lines.append("")
    return lines


def _render_sources(citations: CitationIndex) -> list[str]:
    if not citations.sources:
        return []
    lines = ["**Sources**"]
    for source in citations.sources:
        if source.url:
            lines.append(f"{source.number}. {source.title} — {source.url}")
        else:
            lines.append(f"{source.number}. {source.title}")
    lines.append("")
    return lines


def _evidence_id_sequences(profile: CompetitorProfile):
    for category in ALL_PROFILE_CATEGORIES:
        for claim in getattr(profile, category):
            yield claim.evidence_ids


def build_markdown(
    target_company_name: str, profiles: list[CompetitorProfile], evidence_lookup: dict[str, dict]
) -> str:
    lines = [f"# Competitor analysis briefing: {target_company_name}", ""]

    for profile in profiles:
        citations = build_citation_index(_evidence_id_sequences(profile), evidence_lookup)

        lines.append(f"## {profile.competitor_name}")
        lines.append(
            f"Coverage score: {profile.evidence_coverage_score:.2f} · "
            f"Overall confidence: {profile.overall_confidence.value}"
        )
        lines.append("")
        for category in ALL_PROFILE_CATEGORIES:
            lines.extend(_render_category(category, getattr(profile, category), citations))
        lines.extend(_render_sources(citations))

    return "\n".join(lines)


def classification_label(value: str) -> str:
    try:
        return Classification(value).value.capitalize()
    except ValueError:
        return value
