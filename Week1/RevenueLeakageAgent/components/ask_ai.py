"""Groq-powered chat tab UI."""

import json

import pandas as pd
import streamlit as st

from utils.analytics import execute_ai_query, parse_ai_query
from utils.groq_client import explain_results, groq_is_configured


EXAMPLE_QUESTIONS = [
    "Which customers have the biggest revenue leakage?",
    "What are the top billing issues?",
    "Which region has the highest leakage?",
    "Show the top 5 underbilled invoices.",
    "Are there unusual discounts?",
    "What are the biggest revenue risks?",
    "Summarize the billing data.",
]


def render_ask_ai(dataframe: pd.DataFrame) -> None:
    st.subheader("Ask AI")
    st.caption("Pandas calculates the answer from the filtered data; Groq explains the compact result. The CSV is never sent to the model.")

    with st.expander("Questions you can ask"):
        for question in EXAMPLE_QUESTIONS:
            st.markdown(f"- {question}")

    configured = groq_is_configured()
    if not configured:
        st.warning("GROQ_API_KEY is not set. Add it to your environment and restart the app to enable chat.")

    if "revenue_chat_messages" not in st.session_state:
        st.session_state.revenue_chat_messages = [
            {"role": "assistant", "content": "Ask me about leakage, underbilling, overdue risk, unusual discounts, customers, regions, products, or billing issues."}
        ]

    for message in st.session_state.revenue_chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    question = st.chat_input("Ask a revenue question", disabled=not configured)
    if not question:
        return

    st.session_state.revenue_chat_messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        plan = parse_ai_query(question)
        if plan is None:
            answer = "I can answer questions about summaries, leakage customers, regions, products, billing issues, underbilled invoices, discounts, overdue balances, and revenue risks. Try one of the examples above."
        else:
            result = execute_ai_query(dataframe, plan)
            with st.spinner("Analyzing the calculated result with Groq..."):
                try:
                    answer = explain_results(question, result)
                except (ValueError, RuntimeError) as exc:
                    answer = f"I calculated the result, but could not get a Groq explanation: {exc}\n\nCalculated result:\n```json\n{json.dumps(result, indent=2, default=str)}\n```"
        st.markdown(answer)
    st.session_state.revenue_chat_messages.append({"role": "assistant", "content": answer})

