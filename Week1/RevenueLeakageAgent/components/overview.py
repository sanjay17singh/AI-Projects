"""Overview tab UI."""

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.analytics import kpis


def _money(value: float) -> str:
    return f"${value:,.2f}"


def render_overview(dataframe: pd.DataFrame) -> None:
    st.subheader("Revenue overview")
    metrics = kpis(dataframe)
    first_row = st.columns(3)
    first_row[0].metric("Total Expected Revenue", _money(metrics["expected_revenue"]))
    first_row[1].metric("Total Billed Amount", _money(metrics["billed_amount"]))
    first_row[2].metric("Total Revenue Leakage", _money(metrics["revenue_leakage"]))
    second_row = st.columns(2)
    second_row[0].metric("Total Overdue Amount", _money(metrics["overdue_amount"]))
    second_row[1].metric("Total Invoices", f"{metrics['invoice_count']:,}")

    payment = dataframe.assign(
        payment_group=dataframe["payment_status"].str.strip().str.lower().eq("paid").map(
            {True: "Paid", False: "Unpaid"}
        )
    )
    payment_counts = payment["payment_group"].value_counts().rename_axis("Status").reset_index(name="Invoices")

    revenue_comparison = pd.DataFrame(
        {
            "Revenue Type": ["Expected", "Billed"],
            "Amount": [metrics["expected_revenue"], metrics["billed_amount"]],
        }
    )
    left, right = st.columns(2)
    with left:
        figure = px.pie(
            payment_counts,
            names="Status",
            values="Invoices",
            title="Paid vs Unpaid Invoices",
            hole=0.55,
            color="Status",
            color_discrete_map={"Paid": "#16a34a", "Unpaid": "#f97316"},
        )
        st.plotly_chart(figure, width="stretch")
    with right:
        figure = px.bar(
            revenue_comparison,
            x="Revenue Type",
            y="Amount",
            title="Expected vs Billed Revenue",
            color="Revenue Type",
            text_auto=".3s",
            color_discrete_sequence=["#2563eb", "#14b8a6"],
        )
        figure.update_layout(showlegend=False, yaxis_tickprefix="$")
        st.plotly_chart(figure, width="stretch")

    trend = (
        dataframe.groupby("billing_date", as_index=False)[["expected_amount", "billed_amount"]]
        .sum()
        .sort_values("billing_date")
        .melt("billing_date", var_name="Revenue Type", value_name="Amount")
    )
    trend["Revenue Type"] = trend["Revenue Type"].map(
        {"expected_amount": "Expected", "billed_amount": "Billed"}
    )
    figure = px.line(
        trend,
        x="billing_date",
        y="Amount",
        color="Revenue Type",
        markers=True,
        title="Revenue Trend",
        color_discrete_sequence=["#2563eb", "#14b8a6"],
    )
    figure.update_layout(yaxis_tickprefix="$", xaxis_title="Billing Date")
    st.plotly_chart(figure, width="stretch")
