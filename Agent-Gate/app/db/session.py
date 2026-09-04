"""Database engine/session factory, built via dependency injection.

No module-level global engine — callers (FastAPI dependency, scripts, tests)
construct a SessionFactory from an explicit Settings/database_url so tests can
point at agentgate_test without touching process-wide state.
"""

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings


def make_engine(database_url: str) -> Engine:
    return create_engine(database_url, pool_pre_ping=True)


class SessionFactory:
    def __init__(self, database_url: str):
        self.engine = make_engine(database_url)
        self._sessionmaker = sessionmaker(bind=self.engine, expire_on_commit=False)

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        session = self._sessionmaker()
        try:
            yield session
        finally:
            session.close()


def get_session_factory(settings: Settings | None = None) -> SessionFactory:
    settings = settings or get_settings()
    return SessionFactory(settings.database_url)
