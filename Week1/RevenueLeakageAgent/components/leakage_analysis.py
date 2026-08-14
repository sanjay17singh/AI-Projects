"""Leakage analysis tab UI."""

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.analytics import classify_billing, grouped_leakage


def _money(value: float) -> str:
    return f"${value:,.2f}"


def render_leakage_analysis(dataframe: pd.DataFrame) -> None:
    st.subheader("Leakage analysis")
    st.caption("Leakage is calculated as Expected Amount − Billed Amount. Only positive differences count toward revenue leakage.")
    classified = classify_billing(dataframe)

    underbilled = classified["billing_status"].eq("Underbilled")
    overbilled = classified["billing_status"].eq("Overbilled")
    correctly_billed = classified["billing_status"].eq("Correctly billed")
    metric_columns = st.columns(4)
    metric_columns[0].metric("Underbilled Invoices", f"{int(underbilled.sum()):,}")
    metric_columns[1].metric("Overbilled Invoices", f"{int(overbilled.sum()):,}")
    metric_columns[2].metric("Correctly Billed", f"{int(correctly_billed.sum()):,}")
    metric_columns[3].metric("Total Leakage", _money(classified["positive_leakage"].sum()))
    st.caption(f"Overbilled amount tracked separately: {_money(classified['overbilled_amount'].sum())}")

    customers = grouped_leakage(classified, "customer_id", 10)
    regions = grouped_leakage(classified, "region")
    products = grouped_leakage(classified, "product")
    issues = grouped_leakage(classified, "issue_type")

    left, right = st.columns(2)
    with left:
        figure = px.bar(
            customers.sort_values("leakage"),
            x="leakage",
            y="customer_id",
            orientation="h",
            title="Top Customers with Leakage",
            color="leakage",
            color_continuous_scale="Blues",
        )
        figure.update_layout(xaxis_tickprefix="$", coloraxis_showscale=False)
        st.plotly_chart(figure, width="stretch")
    with right:
        figure = px.bar(
            regions,
            x="region",
            y="leakage",
            title="Leakage by Region",
            color="leakage",
            color_continuous_scale="Oranges",
        )
        figure.update_layout(yaxis_tickprefix="$", coloraxis_showscale=False)
        st.plotly_chart(figure, width="stretch")

    left, right = st.columns(2)
    with left:
        figure = px.bar(
            products,
            x="product",
            y="leakage",
            title="Leakage by Product",
            color="product",
        )
        figure.update_layout(yaxis_tickprefix="$", showlegend=False)
        st.plotly_chart(figure, width="stretch")
    with right:
        figure = px.bar(
            issues,
            x="issue_type",
            y="leakage",
            title="Leakage by Issue Type",
            color="issue_type",
        )
        figure.update_layout(yaxis_tickprefix="$", showlegend=False)
        st.plotly_chart(figure, width="stretch")

    st.markdown("#### Top 10 leakage cases")
    top_cases = classified[classified["positive_leakage"] > 0].nlargest(10, "positive_leakage")[[
        "invoice_id",
        "customer_id",
        "billing_date",
        "region",
        "product",
        "expected_amount",
        "billed_amount",
        "positive_leakage",
        "issue_type",
    ]].rename(columns={"positive_leakage": "leakage_amount"})
    st.dataframe(
        top_cases,
        width="stretch",
        hide_index=True,
        column_config={
            "expected_amount": st.column_config.NumberColumn(format="$%.2f"),
            "billed_amount": st.column_config.NumberColumn(format="$%.2f"),
            "leakage_amount": st.column_config.NumberColumn(format="$%.2f"),
        },
    )
    st.download_button(
        "Download leakage cases",
        classified[classified["positive_leakage"] > 0].to_csv(index=False).encode("utf-8"),
        file_name="revenue_leakage_cases.csv",
        mime="text/csv",
    )
