from collections.abc import Generator
from functools import lru_cache

from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.base import make_engine, make_session_factory


@lru_cache
def _session_factory_for(database_url: str):
    engine = make_engine(database_url)
    return make_session_factory(engine)


def get_session_factory(settings: Settings | None = None):
    settings = settings or get_settings()
    return _session_factory_for(settings.database_url)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a scoped session, closes it after the request."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
