"""Shared helpers for the Streamlit pages."""

import streamlit as st

from app.ui import api_client

SEVERITY_COLOR = {"critical": "red", "high": "orange", "medium": "blue", "low": "gray"}
STATUS_ICON = {
    "passed": ":material/check_circle:",
    "failed": ":material/cancel:",
    "error": ":material/error:",
    "timeout": ":material/schedule:",
    "inconclusive": ":material/help:",
    "completed": ":material/check_circle:",
    "paused_for_human_review": ":material/pause_circle:",
    "running": ":material/sync:",
    "errored": ":material/error:",
    "failed_closed": ":material/lock:",
}
RECOMMENDATION_COLOR = {
    "APPROVE": "green",
    "APPROVE_WITH_CONDITIONS": "orange",
    "BLOCK": "red",
    "INCONCLUSIVE": "gray",
}


def severity_badge(severity: str) -> str:
    color = SEVERITY_COLOR.get(severity, "gray")
    return f":{color}-badge[{severity.upper()}]"


def status_line(status: str) -> str:
    icon = STATUS_ICON.get(status, ":material/help:")
    return f"{icon} {status.replace('_', ' ')}"


def run_selector(key: str = "run_selector") -> str | None:
    try:
        runs = api_client.list_evaluations()
    except api_client.ApiError as exc:
        st.error(f"Could not reach the AgentGate API at `{api_client.BASE_URL}`: {exc.detail}")
        return None

    if not runs:
        st.info("No evaluation runs yet. Start one from **New evaluation**.")
        return None

    options = {f"{r['title']} — {r['run_id'][:8]} ({r['status']})": r["run_id"] for r in runs}
    labels = list(options.keys())
    default_run_id = st.session_state.get("selected_run_id")
    default_index = 0
    for i, run_id in enumerate(options.values()):
        if run_id == default_run_id:
            default_index = i
            break

    selected_label = st.selectbox("Evaluation run", labels, index=default_index, key=key)
    run_id = options[selected_label]
    st.session_state["selected_run_id"] = run_id
    return run_id
