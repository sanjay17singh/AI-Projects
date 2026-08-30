"""T18 (+): alembic upgrade head -> downgrade base -> upgrade head succeeds
cleanly. Skipped unless TEST_DATABASE_URL is set — Alembic's DDL (CREATE
EXTENSION, JSONB, etc.) targets real Postgres, not SQLite."""

import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.config import get_settings

pytestmark = pytest.mark.requires_postgres

EXPECTED_TABLES = {
    "workspaces",
    "runs",
    "discovery_candidates",
    "competitor_selections",
    "research_evidence",
    "competitor_profiles",
    "analysis_claims",
    "run_costs",
    "run_events",
    "briefings",
}


@pytest.fixture
def test_database_url():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL not set — skipping Alembic migration check")
    return url


@pytest.fixture
def alembic_config(test_database_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    get_settings.cache_clear()

    # Defensive full reset: this database is shared with test_t17's real-Postgres
    # check, and this test's own assertions require starting from a state with
    # no alembic_version stamp, regardless of what order tests happened to run in.
    engine = create_engine(test_database_url)
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    engine.dispose()

    cfg = Config("alembic.ini")
    yield cfg
    get_settings.cache_clear()


def test_upgrade_downgrade_upgrade_cycle_succeeds(alembic_config, test_database_url):
    command.upgrade(alembic_config, "head")
    engine = create_engine(test_database_url)
    tables = set(inspect(engine).get_table_names())
    assert EXPECTED_TABLES.issubset(tables)
    engine.dispose()

    command.downgrade(alembic_config, "base")
    engine = create_engine(test_database_url)
    tables_after_downgrade = set(inspect(engine).get_table_names())
    assert EXPECTED_TABLES.isdisjoint(tables_after_downgrade)
    engine.dispose()

    command.upgrade(alembic_config, "head")
    engine = create_engine(test_database_url)
    tables_final = set(inspect(engine).get_table_names())
    assert EXPECTED_TABLES.issubset(tables_final)
    engine.dispose()
