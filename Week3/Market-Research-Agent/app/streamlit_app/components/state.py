import streamlit as st

DEFAULTS = {
    "run_id": None,
    "workspace_id": "default",
    "discovery_status": None,
    "candidates": [],
    "selected_candidate_ids": [],
    "research_status": None,
    "briefing_data": None,
}


def init_state() -> None:
    for key, value in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_run() -> None:
    for key, value in DEFAULTS.items():
        st.session_state[key] = value
