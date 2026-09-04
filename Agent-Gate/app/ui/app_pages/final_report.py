import streamlit as st

from app.ui import api_client
from app.ui.common import RECOMMENDATION_COLOR, run_selector

st.title(":material/summarize: Final report")

run_id = run_selector(key="report_run_selector")
if not run_id:
    st.stop()

report = api_client.get_evaluation_report(run_id)
if report is None:
    st.info("This run hasn't reached Report Generation yet — check **Run details** for progress.")
    st.stop()

color = RECOMMENDATION_COLOR.get(report["recommendation"], "gray")
st.markdown(f"## :{color}-badge[{report['recommendation']}]")
st.caption(report["recommendation_rationale"])

with st.container(horizontal=True):
    st.metric("Scenarios passed", report["scenarios_passed"], border=True)
    st.metric("Scenarios failed", report["scenarios_failed"], border=True)
    st.metric("Semantic coverage", "degraded" if report["semantic_coverage_degraded"] else "full", border=True)

st.subheader("Change summary")
st.write(report["change_summary"])

st.subheader("Risk assessment")
st.write(report["risk_assessment_summary"])

st.subheader("Coverage")
st.write(report["coverage_summary"])

col1, col2 = st.columns(2)
with col1, st.container(border=True):
    st.markdown("**Findings**")
    if report["findings_summary"]:
        for f in report["findings_summary"]:
            st.markdown(f"- {f}")
    else:
        st.caption("None.")
with col2, st.container(border=True):
    st.markdown("**Guardrail recommendations**")
    if report["guardrails_summary"]:
        for g in report["guardrails_summary"]:
            st.markdown(f"- {g}")
    else:
        st.caption("None.")

with st.container(border=True):
    st.markdown("**Human decisions**")
    if report["human_decisions_summary"]:
        for d in report["human_decisions_summary"]:
            st.markdown(f"- {d}")
    else:
        st.caption("None recorded.")

if report["infrastructure_issues_summary"]:
    with st.container(border=True):
        st.markdown("**Infrastructure issues**")
        for i in report["infrastructure_issues_summary"]:
            st.markdown(f"- {i}")

st.divider()
st.caption(
    "Publishing this report externally is itself a human-in-the-loop action in AgentGate's design "
    "(see the HITL requirements) — this MVP surfaces the report for internal review; wiring an explicit "
    "publish/export approval is noted as a post-MVP capability."
)
