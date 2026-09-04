import streamlit as st

from app.ui import api_client
from app.ui.common import RECOMMENDATION_COLOR, run_selector, severity_badge, status_line

st.title(":material/timeline: Run details")

run_id = run_selector()
if not run_id:
    st.stop()

try:
    run = api_client.get_evaluation(run_id)
    state = api_client.get_evaluation_state(run_id)
    scenarios = api_client.get_evaluation_scenarios(run_id)
    findings = api_client.get_evaluation_findings(run_id)
except api_client.ApiError as exc:
    st.error(f"Could not load run: {exc.detail}")
    st.stop()

values = state["values"]

with st.container(horizontal=True):
    st.metric("Status", status_line(run["status"]).split(" ", 1)[-1], border=True)
    st.metric("Active target config", values.get("active_target_config", "-"), border=True)
    st.metric("Loop count (guardrail re-entries)", values.get("loop_count", 0), border=True)
    st.metric("Semantic coverage", "degraded" if run["semantic_coverage_degraded"] else "full", border=True)

if state.get("pending_review"):
    review = state["pending_review"]
    st.warning(
        f":material/pause_circle: Paused at checkpoint — pending **{review['review_type']}** review. "
        f"Available actions: {', '.join(review['available_actions'])}. See **Human review** to decide."
    )
elif state["next_nodes"]:
    st.info(f":material/sync: Next node(s) queued: {', '.join(state['next_nodes'])}")
else:
    st.success(":material/check_circle: Workflow complete for this checkpoint.")

st.subheader("Scenario executions")
if not scenarios:
    st.info("No scenarios executed yet.")
else:
    st.dataframe(
        [
            {
                "Scenario": s["scenario_id"],
                "Attempt": s["attempt"],
                "Target config": s["target_config"],
                "Status": s["status"],
                "Latency (ms)": round(s["latency_ms"], 1),
                "Error": s["error"] or "",
                "Tool calls": len(s["tool_calls"]),
            }
            for s in scenarios
        ],
        hide_index=True,
        width="stretch",
    )
    with st.expander("Tool call detail"):
        for s in scenarios:
            st.markdown(f"**{s['scenario_id']}** (attempt {s['attempt']}, {s['target_config']})")
            for call in s["tool_calls"]:
                icon = ":material/error:" if call.get("error") else ":material/check_circle:"
                st.markdown(f"{icon} `{call['tool_name']}({call['arguments']})` → {call.get('error') or call.get('result')}")

st.subheader("Findings")
if not findings:
    st.success(":material/check_circle: No findings recorded.")
else:
    for f in findings:
        with st.container(border=True):
            cols = st.columns([1, 2, 5, 1])
            cols[0].markdown(severity_badge(f["severity"]))
            cols[1].markdown(f"`{f['scenario_id']}`")
            cols[2].markdown(f["description"])
            cols[3].markdown(f":gray-badge[{f['status']}]")

st.subheader("Guardrail recommendations")
guardrails = values.get("guardrail_recommendations", [])
if not guardrails:
    st.caption("None proposed for this run.")
for g in guardrails:
    with st.container(border=True):
        st.markdown(f"**Status:** :{'green' if g['status']=='approved' else 'orange' if g['status']=='proposed' else 'red'}-badge[{g['status']}]")
        st.markdown(f"**Proposed change:** {g['proposed_change']}")
        st.markdown(f"**Benefit:** {g['benefit']}")
        st.markdown(f"**Side effects:** {g['side_effects']}")
        st.markdown(f"**Rollback guidance:** {g['rollback_guidance']}")

st.subheader("Human decision history")
decisions = values.get("human_decisions", [])
if not decisions:
    st.caption("No human decisions recorded yet.")
for d in decisions:
    with st.container(border=True):
        st.markdown(f"**{d['reviewer']}** — :{'green' if d['decision']=='approve' else 'red'}-badge[{d['decision']}]")
        st.caption(d["justification"])

st.subheader("Infrastructure issues / errors")
infra_issues = values.get("infra_issues", [])
if not infra_issues:
    st.caption("None recorded.")
for i in infra_issues:
    st.error(f"**{i['kind']}** ({i['failure_class']}): {i['detail']}")

if values.get("report"):
    st.subheader("Release recommendation")
    report = values["report"]
    color = RECOMMENDATION_COLOR.get(report["recommendation"], "gray")
    st.markdown(f":{color}-badge[{report['recommendation']}]")
    st.caption(report["recommendation_rationale"])
