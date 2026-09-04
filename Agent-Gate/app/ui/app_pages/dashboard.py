import streamlit as st

from app.ui import api_client
from app.ui.common import RECOMMENDATION_COLOR, status_line

st.title(":material/dashboard: Dashboard")

try:
    health = api_client.health()
except api_client.ApiError as exc:
    st.error(f"Could not reach the AgentGate API at `{api_client.BASE_URL}`: {exc.detail}")
    st.stop()

with st.container(horizontal=True):
    st.metric("Postgres", "OK" if health["checks"]["postgres"] == "ok" else "unavailable", border=True)
    st.metric("Pinecone", health["checks"]["pinecone"].replace("_", " "), border=True)
    st.metric("OpenAI", health["checks"]["openai"].replace("_", " "), border=True)
    st.metric("LangSmith tracing", health["checks"]["langsmith_tracing"], border=True)

try:
    runs = api_client.list_evaluations()
    pending = api_client.get_pending_reviews()
except api_client.ApiError as exc:
    st.error(f"Could not load evaluations: {exc.detail}")
    st.stop()

with st.container(horizontal=True):
    st.metric("Evaluation runs", len(runs), border=True)
    st.metric("Pending human reviews", len(pending), border=True)
    degraded = sum(1 for r in runs if r["semantic_coverage_degraded"])
    st.metric("Runs with degraded coverage", degraded, border=True)

if pending:
    st.warning(f":material/pause_circle: {len(pending)} evaluation(s) are waiting on a human decision — see **Human review**.")

st.subheader("Evaluation runs")
if not runs:
    st.info("No evaluation runs yet. Start one from **New evaluation**.")
else:
    for run in runs:
        with st.container(border=True):
            cols = st.columns([3, 2, 2, 2])
            cols[0].markdown(f"**{run['title']}**  \n`{run['run_id']}`")
            cols[1].markdown(status_line(run["status"]))
            if run["release_decision"]:
                color = RECOMMENDATION_COLOR.get(run["release_decision"], "gray")
                cols[2].markdown(f":{color}-badge[{run['release_decision']}]")
            else:
                cols[2].markdown(":gray-badge[PENDING]")
            if cols[3].button("View", key=f"view-{run['run_id']}", icon=":material/open_in_new:"):
                st.session_state["selected_run_id"] = run["run_id"]
                st.switch_page("app_pages/run_details.py")
