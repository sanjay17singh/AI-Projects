"""Main entry point for the AI Revenue Leakage Identifier Agent."""

from pathlib import Path

import pandas as pd
import streamlit as st

from components.anomaly_detection import render_anomaly_detection
from components.ask_ai import render_ask_ai
from components.leakage_analysis import render_leakage_analysis
from components.overview import render_overview
from utils.data_loader import DataLoadResult, load_revenue_csv


APP_DIR = Path(__file__).resolve().parent
DEFAULT_CSV = APP_DIR / "RevenueLeakage.csv"


st.set_page_config(
    page_title="Revenue Leakage Agent",
    page_icon="💸",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 2rem; padding-bottom: 3rem;}
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #f8fafc, #eef2ff);
        border: 1px solid #e2e8f0;
        border-radius: 0.8rem;
        padding: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_default_data(path: str) -> DataLoadResult:
    return load_revenue_csv(path)


@st.cache_data(show_spinner=False)
def load_uploaded_data(content: bytes) -> DataLoadResult:
    return load_revenue_csv(content)


def apply_filters(dataframe: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.markdown("### Dashboard filters")
    minimum_date = dataframe["billing_date"].min().date()
    maximum_date = dataframe["billing_date"].max().date()
    date_range = st.sidebar.date_input(
        "Billing date range", value=(minimum_date, maximum_date), min_value=minimum_date, max_value=maximum_date
    )

    filtered = dataframe.copy()
    if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
        start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
        filtered = filtered[filtered["billing_date"].between(start, end)]

    filter_columns = {
        "region": "Region",
        "customer_segment": "Customer segment",
        "product": "Product",
        "payment_status": "Payment status",
        "issue_type": "Issue type",
    }
    for column, label in filter_columns.items():
        options = sorted(dataframe[column].dropna().astype(str).unique().tolist())
        selected = st.sidebar.multiselect(label, options)
        if selected:
            filtered = filtered[filtered[column].isin(selected)]
    return filtered


st.title("💸 AI Revenue Leakage Identifier Agent")
st.caption("Find underbilling, overdue exposure, billing anomalies, and revenue risk with validated invoice data.")

uploaded_file = st.sidebar.file_uploader("Upload another revenue CSV", type=["csv"])
if uploaded_file is not None:
    load_result = load_uploaded_data(uploaded_file.getvalue())
    source_name = uploaded_file.name
else:
    load_result = load_default_data(str(DEFAULT_CSV))
    source_name = DEFAULT_CSV.name

for warning in load_result.warnings:
    st.warning(warning)
if not load_result.is_valid:
    for error in load_result.errors:
        st.error(error)
    st.info("Upload a valid CSV containing all 16 required revenue fields to continue.")
    st.stop()

dataframe = load_result.dataframe
assert dataframe is not None
st.sidebar.success(f"Using {source_name} · {len(dataframe):,} valid rows")
filtered_data = apply_filters(dataframe)
if filtered_data.empty:
    st.warning("No invoices match the selected filters. Adjust the filters to continue.")
    st.stop()
st.sidebar.caption(f"Showing {len(filtered_data):,} of {len(dataframe):,} invoices")

overview_tab, leakage_tab, anomaly_tab, ai_tab = st.tabs(
    ["📊 Overview", "💰 Leakage Analysis", "🚨 Anomaly Detection", "🤖 Ask AI"]
)
with overview_tab:
    render_overview(filtered_data)
with leakage_tab:
    render_leakage_analysis(filtered_data)
with anomaly_tab:
    render_anomaly_detection(filtered_data)
with ai_tab:
    render_ask_ai(filtered_data)

