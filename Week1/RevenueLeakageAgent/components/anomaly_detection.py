"""Anomaly detection tab UI."""

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.anomaly import detect_iqr_anomalies


def render_anomaly_detection(dataframe: pd.DataFrame) -> None:
    st.subheader("Anomaly detection")
    st.caption("Find unusually high or low values with the interquartile range (IQR) method.")
    numeric_columns = dataframe.select_dtypes(include="number").columns.tolist()
    preferred = "billing_difference_abs" if "billing_difference_abs" in numeric_columns else numeric_columns[0]
    controls = st.columns([2, 1])
    column = controls[0].selectbox(
        "Numeric column",
        numeric_columns,
        index=numeric_columns.index(preferred),
        format_func=lambda name: name.replace("_", " ").title(),
    )
    multiplier = controls[1].slider(
        "IQR sensitivity",
        min_value=0.5,
        max_value=3.0,
        value=1.5,
        step=0.25,
        help="Lower values flag more records; 1.5 is the conventional setting.",
    )

    try:
        anomalies, lower, upper = detect_iqr_anomalies(dataframe, column, multiplier)
    except ValueError as exc:
        st.error(str(exc))
        return

    metric_columns = st.columns(3)
    metric_columns[0].metric("Anomalies Detected", f"{len(anomalies):,}")
    metric_columns[1].metric("Lower Bound", f"{lower:,.2f}")
    metric_columns[2].metric("Upper Bound", f"{upper:,.2f}")

    chart_data = dataframe[["invoice_id", column]].copy()
    chart_data["Status"] = "Normal"
    chart_data.loc[anomalies.index, "Status"] = "Anomaly"
    figure = px.scatter(
        chart_data,
        x="invoice_id",
        y=column,
        color="Status",
        title=f"{column.replace('_', ' ').title()} by Invoice",
        color_discrete_map={"Normal": "#94a3b8", "Anomaly": "#dc2626"},
        hover_data=["invoice_id"],
    )
    figure.add_hline(y=upper, line_dash="dash", line_color="#dc2626", annotation_text="Upper bound")
    figure.add_hline(y=lower, line_dash="dash", line_color="#2563eb", annotation_text="Lower bound")
    figure.update_layout(xaxis_title="Invoice", xaxis_showticklabels=False)
    st.plotly_chart(figure, width="stretch")

    st.markdown("#### Detected records")
    if anomalies.empty:
        st.info("No anomalies were found at this sensitivity.")
    else:
        display_columns = [
            "invoice_id",
            "customer_id",
            "billing_date",
            "region",
            column,
            "anomaly_direction",
            "expected_amount",
            "billed_amount",
            "overdue_amount",
            "discount_pct",
        ]
        display_columns = list(dict.fromkeys(display_columns))
        st.dataframe(anomalies[display_columns], width="stretch", hide_index=True)
