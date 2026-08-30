import streamlit as st

from app.export.citations import CitationIndex
from app.streamlit_app.components.state import reset_run

_CLASSIFICATION_COLOR = {"direct": "blue", "indirect": "gray", "emerging": "orange"}
_CONFIDENCE_COLOR = {"high": "green", "medium": "orange", "low": "gray"}


def render_back_to_start_button() -> None:
    """Resets the whole run and returns to the Discovery page (the first
    page) — used on every later page so the user is never stuck mid-flow."""
    if st.button("Back to start", icon=":material/arrow_back:", key="back_to_start"):
        reset_run()
        st.switch_page("app_pages/discovery.py")


def classification_badge(classification: str) -> None:
    st.badge(classification.capitalize(), color=_CLASSIFICATION_COLOR.get(classification, "gray"))


def confidence_badge(confidence: str) -> None:
    st.badge(
        f"{confidence.capitalize()} confidence", color=_CONFIDENCE_COLOR.get(confidence, "gray")
    )


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


def render_claim(claim: dict, citations: CitationIndex) -> None:
    if claim.get("is_unsupported"):
        st.caption("Not publicly available.")
        return

    if claim.get("conflicting_group_id"):
        st.warning("Sources disagree — both values are shown below.", icon=":material/warning:")

    cols = st.columns([5, 2])
    with cols[0]:
        text = claim["value"]
        if claim.get("is_inference"):
            text += " _(inference)_"
        if claim.get("evidence_ids"):
            markers = " ".join(f"`{citations.marker_for(eid)}`" for eid in claim["evidence_ids"])
            text += f" {markers}"
        st.markdown(text)
    with cols[1]:
        confidence_badge(claim["confidence"])


def render_category(category: str, claims: list[dict], citations: CitationIndex) -> None:
    st.markdown(f"**{CATEGORY_LABELS.get(category, category)}**")
    for claim in claims:
        render_claim(claim, citations)


def render_sources(citations: CitationIndex) -> None:
    if not citations.sources:
        return
    st.markdown("**Sources**")
    for source in citations.sources:
        if source.url:
            st.markdown(f"{source.number}. [{source.title}]({source.url})")
        else:
            st.markdown(f"{source.number}. {source.title}")
