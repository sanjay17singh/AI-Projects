import streamlit as st

from scenarios.catalog import load_catalog

st.title(":material/menu_book: Scenario library")
st.caption("The mandatory, version-controlled evaluation catalog: 16 adversarial, 16 benign, 8 workflow/resilience scenarios.")

catalog = load_catalog()

with st.container(horizontal=True):
    st.metric("Total scenarios", len(catalog), border=True)
    st.metric("Adversarial", sum(1 for s in catalog if s.bucket == "adversarial"), border=True)
    st.metric("Benign", sum(1 for s in catalog if s.bucket == "benign"), border=True)
    st.metric("Resilience", sum(1 for s in catalog if s.bucket == "resilience"), border=True)

col1, col2, col3 = st.columns(3)
bucket_filter = col1.multiselect("Bucket", ["adversarial", "benign", "resilience"])
risk_filter = col2.multiselect("Risk level", ["low", "medium", "high", "critical"])
tag_query = col3.text_input("Filter by tag", placeholder="e.g. injection")

filtered = catalog
if bucket_filter:
    filtered = [s for s in filtered if s.bucket in bucket_filter]
if risk_filter:
    filtered = [s for s in filtered if s.risk_level in risk_filter]
if tag_query:
    filtered = [s for s in filtered if any(tag_query.lower() in t.lower() for t in s.tags)]

st.caption(f"Showing {len(filtered)} of {len(catalog)} scenarios")

for scenario in filtered:
    with st.expander(f"**{scenario.id}** — {scenario.title}"):
        badge_color = {"critical": "red", "high": "orange", "medium": "blue", "low": "gray"}.get(scenario.risk_level, "gray")
        st.markdown(f":{badge_color}-badge[{scenario.risk_level.upper()}]  ·  `{scenario.category}`  ·  tags: {', '.join(scenario.tags)}")
        st.markdown(f"**Description:** {scenario.description}")
        st.markdown(f"**Expected behavior:** {scenario.expected_behavior}")
        st.markdown(f"**Forbidden behavior:** {scenario.forbidden_behavior}")
        if scenario.retrieved_context:
            st.markdown("**Retrieved context:**")
            for doc in scenario.retrieved_context:
                trust_label = ":green-badge[trusted]" if doc.trusted else ":red-badge[untrusted]"
                st.markdown(f"- {trust_label} *{doc.title}*: {doc.content[:200]}")
        st.markdown("**Deterministic assertions:**")
        for a in scenario.deterministic_assertions:
            st.code(a.model_dump_json(exclude_none=True), language="json")
        if scenario.llm_rubric:
            st.markdown(f"**LLM rubric:** {scenario.llm_rubric}")
