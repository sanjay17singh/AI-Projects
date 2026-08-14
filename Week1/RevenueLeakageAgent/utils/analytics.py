"""All deterministic revenue calculations used by the dashboard and AI."""

import re
from typing import Any

import pandas as pd

from utils.models import AIQueryPlan, QueryIntent


CURRENCY_TOLERANCE = 0.01


def classify_billing(dataframe: pd.DataFrame) -> pd.DataFrame:
    result = dataframe.copy()
    difference = result["expected_amount"] - result["billed_amount"]
    result["billing_status"] = "Correctly billed"
    result.loc[difference > CURRENCY_TOLERANCE, "billing_status"] = "Underbilled"
    result.loc[difference < -CURRENCY_TOLERANCE, "billing_status"] = "Overbilled"
    result["positive_leakage"] = difference.clip(lower=0)
    result["overbilled_amount"] = (-difference).clip(lower=0)
    return result


def kpis(dataframe: pd.DataFrame) -> dict[str, float | int]:
    classified = classify_billing(dataframe)
    return {
        "expected_revenue": float(classified["expected_amount"].sum()),
        "billed_amount": float(classified["billed_amount"].sum()),
        "revenue_leakage": float(classified["positive_leakage"].sum()),
        "overdue_amount": float(classified["overdue_amount"].sum()),
        "invoice_count": int(len(classified)),
    }


def grouped_leakage(dataframe: pd.DataFrame, column: str, limit: int | None = None) -> pd.DataFrame:
    classified = classify_billing(dataframe)
    grouped = (
        classified.groupby(column, as_index=False)
        .agg(
            leakage=("positive_leakage", "sum"),
            expected_amount=("expected_amount", "sum"),
            billed_amount=("billed_amount", "sum"),
            invoices=("invoice_id", "count"),
        )
        .sort_values("leakage", ascending=False)
    )
    return grouped.head(limit) if limit else grouped


def parse_ai_query(question: str) -> AIQueryPlan | None:
    """Map common finance questions to a constrained analytics plan."""
    normalized = question.lower().strip()
    match = re.search(r"\btop\s+(\d+)\b", normalized)
    limit = min(int(match.group(1)), 20) if match else 5

    if "discount" in normalized and any(word in normalized for word in ("unusual", "anomal", "high", "risk")):
        intent = QueryIntent.DISCOUNT_ANOMALIES
    elif "underbill" in normalized or "invoice" in normalized and "leakage" in normalized:
        intent = QueryIntent.UNDERBILLED
    elif "customer" in normalized and any(word in normalized for word in ("leak", "risk", "big", "top", "highest")):
        intent = QueryIntent.TOP_CUSTOMERS
    elif "region" in normalized:
        intent = QueryIntent.TOP_REGIONS
    elif "product" in normalized:
        intent = QueryIntent.TOP_PRODUCTS
    elif "issue" in normalized:
        intent = QueryIntent.TOP_ISSUES
    elif "overdue" in normalized or "payment" in normalized:
        intent = QueryIntent.OVERDUE_RISKS
    elif "risk" in normalized:
        intent = QueryIntent.REVENUE_RISKS
    elif any(word in normalized for word in ("summary", "summarize", "overview", "total")):
        intent = QueryIntent.SUMMARY
    else:
        return None
    return AIQueryPlan(intent=intent, limit=limit)


def execute_ai_query(dataframe: pd.DataFrame, plan: AIQueryPlan) -> dict[str, Any]:
    """Execute an approved query using Pandas and return only compact results."""
    classified = classify_billing(dataframe)
    limit = plan.limit

    if plan.intent == QueryIntent.SUMMARY:
        metrics = kpis(classified)
        metrics["underbilled_invoices"] = int((classified["billing_status"] == "Underbilled").sum())
        metrics["overbilled_invoices"] = int((classified["billing_status"] == "Overbilled").sum())
        return metrics

    group_map = {
        QueryIntent.TOP_CUSTOMERS: "customer_id",
        QueryIntent.TOP_ISSUES: "issue_type",
        QueryIntent.TOP_REGIONS: "region",
        QueryIntent.TOP_PRODUCTS: "product",
    }
    if plan.intent in group_map:
        return {
            "ranking": grouped_leakage(classified, group_map[plan.intent], limit).round(2).to_dict("records")
        }

    if plan.intent == QueryIntent.UNDERBILLED:
        columns = ["invoice_id", "customer_id", "region", "expected_amount", "billed_amount", "positive_leakage", "issue_type"]
        rows = classified[classified["billing_status"] == "Underbilled"].nlargest(limit, "positive_leakage")
        return {"underbilled_invoices": rows[columns].round(2).to_dict("records")}

    if plan.intent == QueryIntent.DISCOUNT_ANOMALIES:
        q1, q3 = classified["discount_pct"].quantile([0.25, 0.75])
        threshold = q3 + 1.5 * (q3 - q1)
        rows = classified[classified["discount_pct"] > threshold].nlargest(limit, "discount_pct")
        columns = ["invoice_id", "customer_id", "discount_pct", "expected_amount", "positive_leakage"]
        return {"iqr_high_threshold": round(float(threshold), 2), "unusual_discounts": rows[columns].round(2).to_dict("records")}

    if plan.intent == QueryIntent.OVERDUE_RISKS:
        rows = classified.nlargest(limit, "overdue_amount")
        columns = ["invoice_id", "customer_id", "payment_status", "overdue_amount", "days_overdue"]
        return {"total_overdue": round(float(classified["overdue_amount"].sum()), 2), "largest_overdue_invoices": rows[columns].round(2).to_dict("records")}

    risk_rows = classified.assign(
        risk_score=classified["positive_leakage"] + classified["overdue_amount"]
    ).nlargest(limit, "risk_score")
    columns = ["invoice_id", "customer_id", "positive_leakage", "overdue_amount", "days_overdue", "issue_type", "risk_score"]
    return {"largest_combined_risks": risk_rows[columns].round(2).to_dict("records")}

