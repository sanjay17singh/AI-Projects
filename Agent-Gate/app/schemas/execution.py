from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.common import ExecutionStatus, TargetConfig


class ChatMessage(BaseModel):
    role: Literal["user", "system", "assistant", "tool"]
    content: str


class RetrievedDocument(BaseModel):
    doc_id: str
    title: str
    content: str
    trusted: bool = False


class ToolCallRecord(BaseModel):
    tool_name: str
    arguments: dict[str, Any]
    result: Any = None
    error: str | None = None
    latency_ms: float = 0.0


class ScenarioPlanItem(BaseModel):
    scenario_id: str
    category: str
    risk_level: str
    rationale: str = ""


class BudgetStatus(BaseModel):
    approved_budget: int
    planned_count: int
    exceeds_budget: bool
    approved_by: str | None = None


class ScenarioExecutionResult(BaseModel):
    scenario_id: str
    run_id: str
    attempt: int = 1
    target_config: TargetConfig
    status: ExecutionStatus
    transcript: list[ChatMessage] = Field(default_factory=list)
    retrieved_context: list[RetrievedDocument] = Field(default_factory=list)
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    final_output: str = ""
    latency_ms: float = 0.0
    error: str | None = None
