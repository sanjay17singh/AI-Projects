import streamlit as st

from app.ui import api_client

st.title(":material/fact_check: Human review")
st.caption("Every pending review here was persisted to PostgreSQL *before* the workflow paused — decisions require a justification and are idempotent on resubmission.")

try:
    pending = api_client.get_pending_reviews()
except api_client.ApiError as exc:
    st.error(f"Could not load pending reviews: {exc.detail}")
    st.stop()

if not pending:
    st.success(":material/check_circle: No pending human reviews.")
    st.stop()

for review in pending:
    with st.container(border=True):
        st.markdown(f"### {review['review_type'].replace('_', ' ').title()} review")
        st.caption(f"Run `{review['run_id']}` · evidence: `{review['evidence_ref']}` · requested {review['created_at']}")

        if review["review_type"] == "budget":
            st.info("The Scenario Design Agent's planned coverage exceeds the approved evaluation budget.")
        elif review["review_type"] == "guardrail":
            st.info("A confirmed finding has a proposed guardrail repair awaiting approval before it is applied.")
        elif review["review_type"] in ("release", "release_override"):
            st.info("Final release decision — required because this change involves refunds/customer data, or the recommendation was BLOCK/INCONCLUSIVE.")

        try:
            run_state = api_client.get_evaluation_state(review["run_id"])
            if run_state["values"].get("report"):
                st.json(run_state["values"]["report"], expanded=False)
        except api_client.ApiError:
            pass

        with st.form(f"decision-form-{review['id']}"):
            reviewer = st.text_input("Reviewer identifier", key=f"reviewer-{review['id']}")
            decision = st.segmented_control(
                "Decision", options=review["available_actions"], key=f"decision-{review['id']}"
            )
            justification = st.text_area("Justification (required)", key=f"justification-{review['id']}")
            submitted = st.form_submit_button("Submit decision", icon=":material/send:", type="primary")

        if submitted:
            if not reviewer or not decision or not justification.strip():
                st.error("Reviewer, decision, and a non-empty justification are all required.")
            else:
                try:
                    result = api_client.submit_human_decision(
                        review_id=review["id"], reviewer=reviewer, decision=decision, justification=justification
                    )
                except api_client.ApiError as exc:
                    st.error(f"Could not submit decision: {exc.detail}")
                else:
                    st.success(f"Decision recorded. Run status: {result['status']}")
                    st.rerun()
