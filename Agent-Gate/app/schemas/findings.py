from pydantic import BaseModel

from app.schemas.common import AssertionSource, FindingSeverity, FindingStatus


class AssertionResult(BaseModel):
    assertion_type: str
    passed: bool
    detail: str
    source: AssertionSource = "deterministic"


class Finding(BaseModel):
    id: str
    run_id: str
    scenario_execution_id: str
    scenario_id: str
    severity: FindingSeverity
    category: str
    assertion_source: AssertionSource
    description: str
    status: FindingStatus = "open"
    evidence_ids: list[str] = []
