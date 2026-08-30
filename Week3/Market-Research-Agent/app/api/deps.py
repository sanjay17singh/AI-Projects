from collections.abc import Generator

from fastapi import Request
from sqlalchemy.orm import Session

from app.config import Settings, get_settings


def get_settings_dep() -> Settings:
    return get_settings()


def get_db(request: Request) -> Generator[Session, None, None]:
    session_factory = request.app.state.session_factory
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


def get_session_factory_dep(request: Request):
    return request.app.state.session_factory


def get_checkpointer_dep(request: Request):
    return getattr(request.app.state, "checkpointer", None)
