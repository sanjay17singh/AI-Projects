"""Pydantic models used to validate uploaded data and AI requests."""

from datetime import date
from enum import Enum
from math import isfinite

from pydantic import BaseModel, ConfigDict, Field, field_validator


REQUIRED_COLUMNS = [
    "invoice_id",
    "customer_id",
    "billing_date",
    "region",
    "customer_segment",
    "product",
    "expected_amount",
    "billed_amount",
    "leakage_amount",
    "billing_variance_pct",
    "discount_pct",
    "payment_status",
    "amount_paid",
    "overdue_amount",
    "days_overdue",
    "issue_type",
]

NUMERIC_COLUMNS = [
    "expected_amount",
    "billed_amount",
    "leakage_amount",
    "billing_variance_pct",
    "discount_pct",
    "amount_paid",
    "overdue_amount",
    "days_overdue",
]


class RevenueRecord(BaseModel):
    """Validated representation of one invoice row."""

    model_config = ConfigDict(str_strip_whitespace=True)

    invoice_id: str = Field(min_length=1)
    customer_id: str = Field(min_length=1)
    billing_date: date
    region: str = Field(min_length=1)
    customer_segment: str = Field(min_length=1)
    product: str = Field(min_length=1)
    expected_amount: float
    billed_amount: float
    leakage_amount: float
    billing_variance_pct: float
    discount_pct: float
    payment_status: str = Field(min_length=1)
    amount_paid: float
    overdue_amount: float
    days_overdue: float = Field(ge=0)
    issue_type: str = Field(min_length=1)

    @field_validator(
        "expected_amount",
        "billed_amount",
        "leakage_amount",
        "billing_variance_pct",
        "discount_pct",
        "amount_paid",
        "overdue_amount",
        "days_overdue",
    )
    @classmethod
    def numbers_must_be_finite(cls, value: float) -> float:
        if not isfinite(value):
            raise ValueError("must be a finite number")
        return value


class QueryIntent(str, Enum):
    SUMMARY = "summary"
    TOP_CUSTOMERS = "top_customers"
    TOP_ISSUES = "top_issues"
    TOP_REGIONS = "top_regions"
    TOP_PRODUCTS = "top_products"
    UNDERBILLED = "underbilled"
    DISCOUNT_ANOMALIES = "discount_anomalies"
    OVERDUE_RISKS = "overdue_risks"
    REVENUE_RISKS = "revenue_risks"


class AIQueryPlan(BaseModel):
    """A constrained plan that maps a question to safe Pandas operations."""

    intent: QueryIntent
    limit: int = Field(default=5, ge=1, le=20)

