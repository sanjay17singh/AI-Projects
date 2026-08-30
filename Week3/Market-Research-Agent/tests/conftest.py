import os

import pytest
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from app.config import Settings
from app.db import models  # noqa: F401 — populates Base.metadata
from app.db.base import Base, make_engine, make_session_factory

# Set this first so a blank OPENAI_API_KEY= line in .env (the normal state
# when no real key is configured yet) can't clobber it — load_dotenv() below
# defaults to never overriding an already-set env var.
os.environ.setdefault("OPENAI_API_KEY", "test-key-not-real")

# Picks up TEST_DATABASE_URL (and nothing else load-bearing) if the user has
# set it in .env — matches the "optional, .env-configured" story in SETUP.md.
# Every other test in this suite is unaffected: they never read os.environ
# for credentials, only the two requires_postgres-marked ones do.
load_dotenv()


@pytest.fixture
def settings() -> Settings:
    return Settings(
        openai_api_key="test-key-not-real",
        youcom_api_key="test-key-not-real",
        pinecone_api_key="test-key-not-real",
        database_url="sqlite:///:memory:",
    )


@pytest.fixture
def db_session() -> Session:
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = make_session_factory(engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def db_session_factory():
    """Returns a callable[[], Session] against one shared in-memory SQLite DB
    — needed by graph-node tests, since nodes each open their own session."""
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = make_session_factory(engine)
    try:
        yield session_factory
    finally:
        engine.dispose()
