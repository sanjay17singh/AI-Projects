# AI Revenue Leakage Identifier Agent

A simple Streamlit dashboard that validates invoice data, calculates revenue leakage with Pandas, visualizes results with Plotly, detects anomalies, and uses Groq to explain compact analytical results.

## Features

- Default `RevenueLeakage.csv` data source plus CSV upload
- Pydantic schema and row validation
- Revenue KPIs, filters, tables, and Plotly charts
- Underbilling, overbilling, and correctly billed classifications
- IQR anomaly detection for any numeric field
- Groq chat where Pandas performs calculations and the LLM only explains results
- Graceful handling of missing files, invalid rows, empty filters, and missing API keys

Revenue leakage is calculated as:

```text
Expected Amount - Billed Amount
```

Only positive differences contribute to total revenue leakage. Overbilling is reported separately.

## Setup with uv

This project uses `uv` exclusively for dependency and virtual-environment management. Install [uv](https://docs.astral.sh/uv/) first, then run:

```bash
uv sync
```

Set the Groq API key in your shell:

```bash
export GROQ_API_KEY="your-api-key"
```

The app defaults to `llama-3.3-70b-versatile`. To select another Groq chat model:

```bash
export GROQ_MODEL="your-model-name"
```

Start the dashboard:

```bash
uv run streamlit run app.py
```

The Overview, Leakage Analysis, and Anomaly Detection tabs work without a Groq key. Only Ask AI requires it.

## CSV schema

Uploaded files must contain these headers:

```text
invoice_id,customer_id,billing_date,region,customer_segment,product,
expected_amount,billed_amount,leakage_amount,billing_variance_pct,
discount_pct,payment_status,amount_paid,overdue_amount,days_overdue,issue_type
```

Invalid rows are skipped with a visible warning. If required columns are missing or no valid rows remain, the dashboard displays an actionable error instead of failing.

## Ask AI privacy and calculation flow

The app recognizes a constrained set of revenue-analysis questions. It validates the request, executes an approved Pandas calculation, and sends only the small aggregated result to Groq for explanation. It never sends the full CSV and never executes generated code.
