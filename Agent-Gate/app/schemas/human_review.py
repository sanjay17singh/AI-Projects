from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import FailureClass, HumanDecisionValue, ReviewStatus, ReviewType


class HumanReviewRequest(BaseModel):
    id: str
    run_id: str
    review_type: ReviewType
    evidence_ref: str
    available_actions: list[str]
    status: ReviewStatus = "pending"
    idempotency_key: str


class HumanDecision(BaseModel):
    id: str
    review_request_id: str
    reviewer: str
    decision: HumanDecisionValue
    justification: str = Field(min_length=1)
    decided_at: datetime


class InfraIssue(BaseModel):
    kind: str
    failure_class: FailureClass
    detail: str
    retried: bool = False
