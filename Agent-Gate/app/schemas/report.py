from pydantic import BaseModel

from app.schemas.common import ReleaseRecommendation


class EvaluationReport(BaseModel):
    run_id: str
    change_summary: str
    risk_assessment_summary: str
    coverage_summary: str
    scenarios_passed: int
    scenarios_failed: int
    findings_summary: list[str]
    guardrails_summary: list[str]
    human_decisions_summary: list[str]
    infrastructure_issues_summary: list[str]
    semantic_coverage_degraded: bool
    recommendation: ReleaseRecommendation
    recommendation_rationale: str
