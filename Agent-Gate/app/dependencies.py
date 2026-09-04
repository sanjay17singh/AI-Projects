"""Dependency-injection container for external services.

Every agent/graph node receives an AgentDeps instance instead of importing a
global client — this is what lets tests substitute a fake retriever/session
factory without monkeypatching module globals.
"""

from dataclasses import dataclass, field

from app.config import Settings, get_settings
from app.db.session import SessionFactory, get_session_factory
from app.retrieval.fallback import Retriever
from app.retrieval.pinecone_client import PineconeRetriever
from app.tracing.langsmith import get_tracing_callbacks


@dataclass
class AgentDeps:
    settings: Settings
    session_factory: SessionFactory
    retriever: Retriever
    tracing_callbacks: list = field(default_factory=list)


def build_default_deps(settings: Settings | None = None) -> AgentDeps:
    settings = settings or get_settings()
    return AgentDeps(
        settings=settings,
        session_factory=get_session_factory(settings),
        retriever=PineconeRetriever(settings),
        tracing_callbacks=get_tracing_callbacks(settings),
    )
