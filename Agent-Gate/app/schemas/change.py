from pydantic import BaseModel, Field

from app.schemas.common import ChangeType


class ProposedChange(BaseModel):
    id: str
    tenant_id: str = "default"
    change_type: ChangeType
    title: str
    diff_summary: str
    raw_payload: dict = Field(default_factory=dict)
    created_by: str


class RiskAssessment(BaseModel):
    affected_behaviors: list[str]
    risk_categories: list[str]
    relevant_policies: list[str]
    required_coverage_categories: list[str]
    overall_risk_level: str
    rationale: str
