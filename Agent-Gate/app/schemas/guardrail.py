from pydantic import BaseModel

from app.schemas.common import GuardrailStatus


class GuardrailRecommendation(BaseModel):
    id: str
    run_id: str
    finding_id: str
    failure_summary: str
    proposed_change: str
    benefit: str
    side_effects: str
    validation_scenarios: list[str]
    rollback_guidance: str
    status: GuardrailStatus = "proposed"
