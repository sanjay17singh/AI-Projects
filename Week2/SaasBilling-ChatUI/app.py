"""Streamlit chat UI for the SaaS billing & subscription support bot."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

load_dotenv()

from schemas import CATEGORY_LABELS  # noqa: E402

st.set_page_config(page_title="Billing Support", page_icon="💬", layout="centered")


@st.cache_resource(show_spinner=False)
def _load_graph_runner():
    import graph as graph_module

    return graph_module.run


def _init_state() -> None:
    if "customer_id" not in st.session_state:
        st.session_state.customer_id = f"cust-{uuid.uuid4().hex[:8]}"
    if "messages" not in st.session_state:
        st.session_state.messages = []  # list of {role, content, result?}
    if "latest_memory" not in st.session_state:
        st.session_state.latest_memory = None


def _reset_conversation() -> None:
    st.session_state.messages = []
    st.session_state.latest_memory = None


def _render_customer_context(sidebar) -> None:
    sidebar.subheader("Customer context")
    memory = st.session_state.latest_memory
    if not memory:
        sidebar.caption("No memory loaded yet for this customer.")
        return

    if memory.plan_tier:
        sidebar.markdown(f"**Plan tier:** {memory.plan_tier}")
    if memory.prior_issues:
        sidebar.markdown("**Prior issues:**")
        for issue in memory.prior_issues[-5:]:
            sidebar.caption(f"- {issue}")
    if memory.prior_escalations:
        sidebar.markdown("**Prior escalations:**")
        for esc in memory.prior_escalations[-5:]:
            sidebar.caption(f"- {esc.category}: {esc.reason or 'n/a'}")
    if memory.preferences:
        sidebar.markdown("**Preferences:**")
        for pref in memory.preferences[-5:]:
            sidebar.caption(f"- {pref}")
    if not any([memory.plan_tier, memory.prior_issues, memory.prior_escalations, memory.preferences]):
        sidebar.caption("No durable memory recorded for this customer yet.")


def _render_retrieval_breakdown(container, docs: list, debug: dict | None, *, use_columns: bool) -> None:
    """Shows dense vs. BM25 pre-fusion ranks and the RRF-fused final order, inside the
    per-message "How I got this answer" expander."""

    if not debug:
        container.caption("No retrieval breakdown available yet — ask a question first.")
        return

    container.caption("Fusion weights — Dense (Pinecone): 0.50 · BM25 (keyword): 0.50 · RRF constant c=60")

    dense_table = [
        {"rank": d.dense_rank, "source_id": d.source_id, "category": d.category} for d in debug["dense"]
    ]
    bm25_table = [{"rank": d.bm25_rank, "source_id": d.source_id, "category": d.category} for d in debug["bm25"]]
    fused_table = [
        {
            "final_rank": i + 1,
            "source_id": d.source_id,
            "dense_rank": d.dense_rank,
            "bm25_rank": d.bm25_rank,
            "rrf_score": round(d.rrf_score, 4) if d.rrf_score is not None else None,
        }
        for i, d in enumerate(docs or [])
    ]

    if use_columns:
        col_dense, col_bm25 = container.columns(2)
        col_dense.caption("Dense search (Pinecone) — before fusion")
        col_dense.dataframe(dense_table, hide_index=True, use_container_width=True)
        col_bm25.caption("BM25 search (keyword) — before fusion")
        col_bm25.dataframe(bm25_table, hide_index=True, use_container_width=True)
    else:
        container.caption("Dense search (Pinecone) — before fusion")
        container.dataframe(dense_table, hide_index=True, use_container_width=True)
        container.caption("BM25 search (keyword) — before fusion")
        container.dataframe(bm25_table, hide_index=True, use_container_width=True)

    container.caption("Fused result (after RRF) — this ranking is what generation actually used")
    container.dataframe(fused_table, hide_index=True, use_container_width=True)


def _render_bot_message(result: dict) -> None:
    category = result.get("category", "general_policy")
    category_label = CATEGORY_LABELS.get(category, category)

    if result.get("escalate"):
        st.info(
            "🧑‍💼 I want to make sure this is handled correctly — connecting you with a specialist now.",
            icon="🧑‍💼",
        )
        st.caption(f"Category: {category_label} · Status: Escalated to a specialist")
    else:
        st.markdown(result.get("answer") or "I'm not able to answer that right now.")
        docs = result.get("retrieved_docs") or []
        if docs:
            top_source = docs[0]
            st.caption(f"Source: {top_source.label} · Category: {category_label} · ✅ Answered")
        else:
            st.caption(f"Category: {category_label} · ✅ Answered")

    with st.expander("How I got this answer", expanded=False):
        st.markdown(f"**Confidence:** {result.get('confidence', 0.0):.2f}")
        st.markdown(f"**Category:** {category_label}")
        if result.get("dollar_amount"):
            st.markdown(f"**Dollar amount detected:** ${result['dollar_amount']:,.2f}")
        st.markdown(f"**Escalated:** {'Yes' if result.get('escalate') else 'No'}")
        if result.get("escalation_reason"):
            st.markdown(f"**Escalation reason:** {result['escalation_reason']}")
        docs = result.get("retrieved_docs") or []
        if docs:
            st.markdown("**Retrieved sources (final, after fusion):**")
            for d in docs:
                st.markdown(f"- `{d.source_id}` ({d.source_type}/{d.category}): {d.text[:180]}...")
        if result.get("citations"):
            st.markdown(f"**Cited sources:** {', '.join(result['citations'])}")

        debug = result.get("retrieval_debug")
        if debug:
            st.divider()
            st.markdown("**Hybrid retrieval breakdown**")
            _render_retrieval_breakdown(st, docs, debug, use_columns=True)


def main() -> None:
    _init_state()

    with st.sidebar:
        st.header("Billing Support")
        st.text_input("Customer ID", key="customer_id", help="Used to look up long-term memory across sessions.")
        if st.button("Reset conversation", use_container_width=True):
            _reset_conversation()
            st.rerun()
        st.divider()
        _render_customer_context(st.sidebar)

    st.title("💬 Billing Support")
    st.caption("Ask about refunds, billing, plans, invoices, or your subscription.")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant":
                _render_bot_message(msg["result"])
            else:
                st.markdown(msg["content"])

    user_input = st.chat_input("Type your billing question...")
    if not user_input:
        return

    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Looking into that..."):
            try:
                run = _load_graph_runner()
                result = run(st.session_state.customer_id, user_input)
            except Exception as e:
                result = {
                    "answer": None,
                    "citations": [],
                    "confidence": 0.0,
                    "category": "general_policy",
                    "dollar_amount": None,
                    "escalate": True,
                    "escalation_reason": f"System error: {e}",
                    "retrieved_docs": [],
                }
        st.session_state.latest_memory = result.get("memory")
        _render_bot_message(result)

    st.session_state.messages.append({"role": "assistant", "result": result})
    st.rerun()  # so the sidebar's customer context reflects this turn immediately


if __name__ == "__main__":
    main()
