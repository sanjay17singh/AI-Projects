import streamlit as st

from app.streamlit_app.components import api_client, rendering
from app.streamlit_app.components.state import init_state

init_state()

st.title("Find your organization's competitors")

if not st.session_state["run_id"]:
    with st.form("discovery_form"):
        target_company_name = st.text_input("Target company name", max_chars=500)
        col1, col2 = st.columns(2)
        with col1:
            target_company_website = st.text_input("Company website (optional)")
            industry = st.text_input("Industry (optional)")
        with col2:
            geography = st.text_input("Geography (optional)")
            customer_segment = st.text_input("Customer segment (optional)")
        news_window_days = st.selectbox("News window", [30, 60, 90, 180, 365], index=1)

        submitted = st.form_submit_button("Find competitors")
        if submitted:
            if not target_company_name.strip():
                st.error("Target company name is required.")
            else:
                payload = {
                    "target_company_name": target_company_name,
                    "target_company_website": target_company_website or None,
                    "industry": industry or None,
                    "geography": geography or None,
                    "customer_segment": customer_segment or None,
                    "news_window_days": news_window_days,
                }
                try:
                    result = api_client.create_discovery_run(payload)
                    st.session_state["run_id"] = result["run_id"]
                    st.session_state["discovery_status"] = result["status"]
                    st.rerun()
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Could not start discovery: {exc}")

else:
    run_id = st.session_state["run_id"]

    @st.fragment(run_every="2s")
    def poll_discovery() -> None:
        try:
            data = api_client.get_discovery_run(run_id)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Could not fetch discovery status: {exc}")
            return

        st.session_state["discovery_status"] = data["status"]
        st.session_state["candidates"] = data["candidates"]

        if data["status"] in ("discovery_pending",):
            st.info("Searching for competitors…", icon=":material/search:")
            return
        if data["status"] == "discovery_failed":
            st.error(f"Discovery failed: {data.get('error_message', 'unknown error')}")
            if st.button("Start over"):
                st.session_state["run_id"] = None
                st.rerun()
            return

        candidates = data["candidates"]
        st.subheader(f"{len(candidates)} likely competitors found")
        st.caption("Select exactly three to research in depth.")

        with st.form("selection_form"):
            checked_ids = []
            for candidate in candidates:
                with st.container(border=True):
                    header_cols = st.columns([5, 2, 2])
                    with header_cols[0]:
                        st.markdown(
                            f"**{candidate['company_name']}**  \n{candidate['website'] or ''}"
                        )
                    with header_cols[1]:
                        rendering.classification_badge(candidate["classification"])
                    with header_cols[2]:
                        st.metric(
                            "Match score",
                            f"{candidate['match_score']:.2f}",
                            label_visibility="collapsed",
                        )
                    st.write(candidate["explanation"])
                    if candidate["source_urls"]:
                        st.caption("Sources: " + ", ".join(candidate["source_urls"]))
                    picked = st.checkbox("Select this competitor", key=f"pick_{candidate['id']}")
                    if picked:
                        checked_ids.append(candidate["id"])

            submitted = st.form_submit_button("Continue to research")
            if submitted:
                if len(checked_ids) != 3:
                    st.error(
                        f"Select exactly 3 competitors (currently {len(checked_ids)} selected)."
                    )
                else:
                    try:
                        api_client.select_competitors(run_id, checked_ids)
                        st.session_state["selected_candidate_ids"] = checked_ids
                        st.switch_page("app_pages/research_progress.py")
                    except ValueError as exc:
                        st.error(str(exc))
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"Could not save selection: {exc}")

    poll_discovery()
