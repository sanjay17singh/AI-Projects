from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    pass


def make_engine(database_url: str):
    if database_url.startswith("sqlite"):
        # StaticPool keeps exactly one connection alive for the engine's
        # lifetime. Without it, an in-memory SQLite DB is per-connection —
        # FastAPI's TestClient runs the ASGI app (incl. lifespan) in a
        # separate thread, and SQLAlchemy's default SingletonThreadPool is
        # thread-local, so that thread would otherwise see a second, empty
        # database with none of the tables created via Base.metadata.create_all().
        return create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            future=True,
        )
    return create_engine(database_url, future=True)


def make_session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
