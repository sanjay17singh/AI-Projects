"""FastAPI dependency wiring — one AgentDeps + checkpointer per request."""

from collections.abc import Generator

from app.config import Settings, get_settings
from app.db.checkpointer import get_checkpointer
from app.dependencies import AgentDeps, build_default_deps


def get_agent_deps() -> AgentDeps:
    return build_default_deps()


def get_request_checkpointer(settings: Settings | None = None) -> Generator:
    settings = settings or get_settings()
    with get_checkpointer(settings) as cp:
        yield cp
