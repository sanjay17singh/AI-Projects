import streamlit as st

from app.streamlit_app.components import api_client, rendering

rendering.render_back_to_start_button()
st.title("Researching competitors")

run_id = st.session_state.get("run_id")
if not run_id:
    st.info("Start a new search from the Discovery page first.")
    st.stop()


@st.fragment(run_every="3s")
def poll_research() -> None:
    try:
        data = api_client.get_research_status(run_id)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not fetch research status: {exc}")
        return

    status = data["status"]
    budget = data["budget"]

    if budget["awaiting_approval"]:
        with st.container(border=True):
            st.warning(
                f"Research is projected to cost ${budget['projected']:.2f}, over the "
                f"${budget['limit']:.2f} limit. Approve additional budget to continue.",
                icon=":material/warning:",
            )
            new_limit = st.number_input(
                "New budget limit (USD)",
                min_value=budget["limit"],
                value=max(budget["limit"] * 2, 5.0),
                step=0.5,
            )
            if st.button("Approve budget", type="primary"):
                try:
                    api_client.approve_budget(run_id, new_limit)
                    st.rerun()
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Could not approve budget: {exc}")
        return

    st.caption(
        f"Budget: ${budget['actual']:.2f} of ${budget['limit']:.2f} used"
        + (f" (projected ${budget['projected']:.2f})" if budget["projected"] else "")
    )

    phase_icons = {
        "queued": ":material/schedule:",
        "researching": ":material/travel_explore:",
        "analyzing": ":material/analytics:",
        "complete": ":material/check_circle:",
        "failed": ":material/error:",
    }
    cols = st.columns(len(data["competitors"])) if data["competitors"] else []
    for col, competitor in zip(cols, data["competitors"], strict=True):
        with col, st.container(border=True):
            st.markdown(f"**{competitor['name']}**")
            st.caption(
                f"{competitor['phase'].capitalize()} {phase_icons.get(competitor['phase'], '')}"
            )
            st.caption(f"{competitor['evidence_count']} sources gathered")

    if status == "complete":
        st.success("Research complete.")
        if st.button("View briefing", type="primary"):
            st.switch_page("app_pages/briefing.py")
    elif status == "failed":
        st.error("This run failed. See the Discovery page to start a new search.")


poll_research()
