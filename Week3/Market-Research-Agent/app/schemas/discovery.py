from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import Classification, RunStatus


class DiscoveryRequest(BaseModel):
    target_company_name: str = Field(min_length=1, max_length=500)
    target_company_website: str | None = None
    industry: str | None = None
    geography: str | None = None
    customer_segment: str | None = None
    news_window_days: Literal[30, 60, 90, 180, 365] = 60


class NormalizedRequest(BaseModel):
    """Fills gaps in the raw request (e.g. infers industry when not given).
    Content generation only — carries no routing decision."""

    target_company_name: str
    target_company_website: str | None = None
    industry: str
    geography: str
    customer_segment: str
    news_window_days: int
    assumptions: list[str] = Field(
        default_factory=list, description="Plain-language notes on any gaps that were filled in."
    )


class SearchQueryList(BaseModel):
    queries: list[str] = Field(min_length=1, max_length=6)


class CompetitorCandidate(BaseModel):
    company_name: str
    website: str | None = None
    match_score: float = Field(ge=0.0, le=1.0)
    classification: Classification
    explanation: str
    source_urls: list[str] = Field(default_factory=list)


class CandidateList(BaseModel):
    candidates: list[CompetitorCandidate]


class DiscoveryCandidateOut(BaseModel):
    id: UUID
    company_name: str
    website: str | None
    match_score: float
    classification: Classification
    explanation: str
    source_urls: list[str]
    rank: int

    model_config = {"from_attributes": True}


class DiscoveryResponse(BaseModel):
    run_id: UUID
    status: RunStatus
    candidates: list[DiscoveryCandidateOut] = Field(default_factory=list)
    error_message: str | None = None


class DiscoveryRunCreated(BaseModel):
    run_id: UUID
    status: RunStatus = RunStatus.DISCOVERY_PENDING


class SelectionRequest(BaseModel):
    competitor_candidate_ids: list[UUID]


class SelectionResponse(BaseModel):
    run_id: UUID
    status: RunStatus
