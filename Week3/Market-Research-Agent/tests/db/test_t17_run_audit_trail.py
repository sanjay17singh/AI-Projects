"""T17 (+): creating a run writes a runs row + a RUN_CREATED run_events row.
Runs against SQLite by default; also runs against a real Postgres when
TEST_DATABASE_URL is set (skipped otherwise)."""

import os

import pytest
from sqlalchemy import text

from app.db import models  # noqa: F401
from app.db.base import Base, make_engine, make_session_factory
from app.db.models import RunEvent
from app.schemas.discovery import DiscoveryRequest
from app.services.run_service import create_run, ensure_default_workspace


def test_create_run_writes_run_and_run_created_event(db_session):
    workspace = ensure_default_workspace(db_session)
    run = create_run(db_session, workspace.id, DiscoveryRequest(target_company_name="Acme"), 5.0)

    assert run.status == "discovery_pending"
    assert float(run.budget_usd_limit) == 5.0

    events = db_session.query(RunEvent).filter_by(run_id=run.id).all()
    assert len(events) == 1
    assert events[0].event_type == "RUN_CREATED"


@pytest.mark.requires_postgres
def test_create_run_writes_run_and_event_against_real_postgres():
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL not set — skipping real-Postgres audit trail check")

    engine = make_engine(database_url)
    # Full reset first — this database is also used by test_t18's Alembic
    # migration cycle, and a prior alembic_version stamp left over from that
    # test would make Base.metadata.create_all/drop_all here disagree with
    # what Alembic thinks is the current schema state.
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))

    Base.metadata.create_all(engine)
    session_factory = make_session_factory(engine)
    db = session_factory()
    try:
        workspace = ensure_default_workspace(db)
        run = create_run(db, workspace.id, DiscoveryRequest(target_company_name="Acme (pg)"), 5.0)
        events = db.query(RunEvent).filter_by(run_id=run.id).all()
        assert len(events) == 1
        assert events[0].event_type == "RUN_CREATED"
    finally:
        db.rollback()
        db.close()
        with engine.begin() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
        engine.dispose()
