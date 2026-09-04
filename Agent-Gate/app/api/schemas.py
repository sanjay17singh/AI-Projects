"""Request/response bodies for the FastAPI layer. Kept separate from the
internal agent/state schemas in app/schemas/ since the API surface can evolve
independently of the graph's internal representation.
"""

from pydantic import BaseModel

from app.schemas.common import ChangeType, HumanDecisionValue


class CreateEvaluationRequest(BaseModel):
    tenant_id: str = "default"
    change_type: ChangeType
    title: str
    diff_summary: str
    raw_payload: dict = {}
    created_by: str


class CreateEvaluationResponse(BaseModel):
    run_id: str
    thread_id: str
    status: str
    pending_review: dict | None = None


class HumanDecisionRequest(BaseModel):
    review_id: str
    reviewer: str
    decision: HumanDecisionValue
    justification: str
    idempotency_key: str | None = None


class HumanDecisionResponse(BaseModel):
    run_id: str
    status: str
    pending_review: dict | None = None
