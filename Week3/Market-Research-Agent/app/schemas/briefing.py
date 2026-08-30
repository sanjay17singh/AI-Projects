from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.analysis import CompetitorProfile


class CoverageSummary(BaseModel):
    competitors_profiled: int
    sources_cited: int
    overall_coverage_label: str  # "high" | "medium" | "low" — see analysis_service


class UnresolvedConflict(BaseModel):
    competitor_name: str
    field_name: str
    values: list[str]


class Briefing(BaseModel):
    run_id: UUID
    target_company_name: str
    generated_at: datetime
    coverage_summary: CoverageSummary
    profiles: list[CompetitorProfile]
    unresolved_conflicts: list[UnresolvedConflict] = Field(default_factory=list)
    markdown_content: str
    # evidence_id -> {"url":..., "title":...} for every citation referenced
    # across `profiles` — lets a consumer (e.g. the Streamlit page) render
    # footnote-style [1], [2]... numbering itself via app/export/citations.py,
    # without needing its own DB access.
    evidence_sources: dict[str, dict] = Field(default_factory=dict)
