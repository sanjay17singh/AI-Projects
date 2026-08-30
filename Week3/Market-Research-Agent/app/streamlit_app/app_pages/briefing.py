import streamlit as st

from app.export.citations import build_citation_index
from app.schemas.common import ALL_PROFILE_CATEGORIES
from app.streamlit_app.components import api_client, rendering

rendering.render_back_to_start_button()
st.title("Competitor analysis briefing")

run_id = st.session_state.get("run_id")
if not run_id:
    st.info("Start a new search from the Discovery page first.")
    st.stop()

briefing = api_client.get_briefing(run_id)
if briefing is None:
    st.info("The briefing isn't ready yet — check the Research progress page.")
    st.stop()

coverage = briefing["coverage_summary"]
cols = st.columns(3)
cols[0].metric("Competitors profiled", coverage["competitors_profiled"])
cols[1].metric("Sources cited", coverage["sources_cited"])
cols[2].metric("Overall coverage", coverage["overall_coverage_label"].capitalize())

export_cols = st.columns(3)
for col, (fmt, mime, label) in zip(
    export_cols,
    [
        ("markdown", "text/markdown", "Download Markdown"),
        ("csv", "text/csv", "Download CSV"),
        ("pdf", "application/pdf", "Download PDF"),
    ],
    strict=True,
):
    with col:
        try:
            content = api_client.export_briefing(run_id, fmt)
            st.download_button(
                label,
                data=content,
                file_name=f"briefing-{run_id}.{fmt if fmt != 'markdown' else 'md'}",
                mime=mime,
                width="stretch",
            )
        except Exception as exc:  # noqa: BLE001
            st.caption(f"{label} unavailable: {exc}")

profiles = briefing["profiles"]
evidence_sources = briefing["evidence_sources"]
tabs = st.tabs([p["competitor_name"] for p in profiles])
for tab, profile in zip(tabs, profiles, strict=True):
    with tab:
        header_cols = st.columns([3, 2, 2])
        with header_cols[1]:
            st.metric("Coverage score", f"{profile['evidence_coverage_score']:.2f}")
        with header_cols[2]:
            rendering.confidence_badge(profile["overall_confidence"])

        citations = build_citation_index(
            (
                claim["evidence_ids"]
                for category in ALL_PROFILE_CATEGORIES
                for claim in profile[category]
            ),
            evidence_sources,
        )
        for category in ALL_PROFILE_CATEGORIES:
            rendering.render_category(category, profile[category], citations)
        rendering.render_sources(citations)
