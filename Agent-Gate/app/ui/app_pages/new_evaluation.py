import uuid

import streamlit as st

from app.ui import api_client

st.title(":material/add_circle: New evaluation")
st.caption("Submit a proposed change to an AI agent for AgentGate to evaluate against the mandatory scenario catalog.")

with st.form("new_evaluation_form"):
    title = st.text_input("Change title", placeholder="Enable knowledge-base retrieval for refund FAQ answers")
    change_type = st.selectbox("Change type", ["prompt", "model", "tool", "policy", "retrieval"])
    diff_summary = st.text_area(
        "Diff summary",
        placeholder="Describe what changed and why (this feeds the Change Analysis Agent's risk assessment).",
        height=120,
    )
    created_by = st.text_input("Your identifier (email or username)", placeholder="it@intellious.tech")
    tenant_id = st.text_input("Tenant ID", value="default")
    submitted = st.form_submit_button("Start evaluation", icon=":material/rocket_launch:", type="primary")

if submitted:
    if not title or not diff_summary or not created_by:
        st.error("Title, diff summary, and your identifier are all required.")
    else:
        idempotency_key = str(uuid.uuid4())
        try:
            with st.spinner("Running Change Analysis, Scenario Design, and Sandbox Execution..."):
                result = api_client.create_evaluation(
                    tenant_id=tenant_id,
                    change_type=change_type,
                    title=title,
                    diff_summary=diff_summary,
                    raw_payload={},
                    created_by=created_by,
                    idempotency_key=idempotency_key,
                )
        except api_client.ApiError as exc:
            st.error(f"Evaluation failed to start: {exc.detail}")
        else:
            st.session_state["selected_run_id"] = result["run_id"]
            st.success(f"Evaluation `{result['run_id']}` created — status: {result['status']}")
            if result.get("pending_review"):
                st.info(
                    f":material/pause_circle: Paused for human review "
                    f"({result['pending_review']['review_type']}) — see **Human review**."
                )
            if st.button("Go to run details", icon=":material/timeline:"):
                st.switch_page("app_pages/run_details.py")
