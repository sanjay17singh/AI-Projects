"""Fixtures for workflow tests: real Postgres (agentgate_test), fake LLM/tool
execution so no OpenAI/Pinecone credentials are required.
"""

import pytest
from sqlalchemy import text

from app.config import Settings
from app.db.checkpointer import get_checkpointer
from app.db.models import Base
from app.db.session import get_session_factory
from app.dependencies import AgentDeps
from app.retrieval.pinecone_client import PineconeRetriever

TEST_DATABASE_URL = "postgresql+psycopg://localhost/agentgate_test"


@pytest.fixture
def test_settings() -> Settings:
    return Settings(database_url=TEST_DATABASE_URL, pinecone_api_key="", openai_api_key="")


@pytest.fixture(autouse=True)
def clean_business_tables(test_settings):
    """Workflow tests exercise real dedup/idempotency logic against a real
    Postgres instance — that only behaves predictably if each test starts
    from an empty business schema (checkpoint tables are separate and are
    truncated too, since each test picks a fresh thread_id anyway).
    """
    factory = get_session_factory(test_settings)
    table_names = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    with factory.session() as session:
        session.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"))
        session.execute(text("TRUNCATE TABLE checkpoints, checkpoint_writes, checkpoint_blobs RESTART IDENTITY CASCADE"))
        session.commit()
    yield


@pytest.fixture
def deps(test_settings) -> AgentDeps:
    return AgentDeps(
        settings=test_settings,
        session_factory=get_session_factory(test_settings),
        retriever=PineconeRetriever(test_settings),
        tracing_callbacks=[],
    )


@pytest.fixture
def checkpointer(test_settings):
    with get_checkpointer(test_settings) as cp:
        yield cp
