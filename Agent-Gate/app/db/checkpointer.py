"""LangGraph PostgreSQL checkpointing.

Physically separate from the business/audit schema (app/db/models.py) — the
checkpointer owns and migrates its own tables via its own setup() call, run
once from scripts/setup_checkpointer.py, never via Alembic.
"""

from contextlib import contextmanager

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.serde.base import maybe_add_typed_methods
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from app.config import Settings, get_settings
from app.schemas.change import ProposedChange, RiskAssessment
from app.schemas.execution import (
    BudgetStatus,
    ChatMessage,
    RetrievedDocument,
    ScenarioExecutionResult,
    ScenarioPlanItem,
    ToolCallRecord,
)
from app.schemas.findings import AssertionResult, Finding
from app.schemas.guardrail import GuardrailRecommendation
from app.schemas.human_review import HumanDecision, HumanReviewRequest, InfraIssue
from app.schemas.report import EvaluationReport

# Every Pydantic model that can ever appear inside AgentGateState (app/schemas/state.py)
# gets msgpack'd into a checkpoint. LangGraph's checkpoint serializer only allows
# arbitrary Python types by default with a "this will be blocked in a future
# version" warning — explicitly allow-listing our own known types here is both
# the fix for that warning and, per LangGraph's own security note on
# JsonPlusSerializer, the right way to run it: checkpoints should only ever
# deserialize types this application actually wrote, nothing else.
CHECKPOINT_ALLOWED_TYPES = [
    ProposedChange,
    RiskAssessment,
    ChatMessage,
    RetrievedDocument,
    ToolCallRecord,
    ScenarioPlanItem,
    BudgetStatus,
    ScenarioExecutionResult,
    AssertionResult,
    Finding,
    GuardrailRecommendation,
    HumanReviewRequest,
    HumanDecision,
    InfraIssue,
    EvaluationReport,
]


def _checkpoint_serde() -> JsonPlusSerializer:
    return JsonPlusSerializer(allowed_msgpack_modules=CHECKPOINT_ALLOWED_TYPES)


def _bind_serde(saver: PostgresSaver) -> PostgresSaver:
    saver.serde = maybe_add_typed_methods(_checkpoint_serde())
    return saver


@contextmanager
def get_checkpointer(settings: Settings | None = None):
    settings = settings or get_settings()
    with PostgresSaver.from_conn_string(settings.psycopg_dsn) as saver:
        yield _bind_serde(saver)


def setup_checkpoint_tables(settings: Settings | None = None) -> None:
    """Creates the langgraph checkpoint tables if they don't exist. Idempotent."""
    settings = settings or get_settings()
    with PostgresSaver.from_conn_string(settings.psycopg_dsn) as saver:
        saver.setup()
