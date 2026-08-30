import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routers import briefing, discovery, health, research, selection
from app.clients.langsmith_client import init_tracing
from app.clients.pinecone_client import PineconeClient
from app.config import get_settings
from app.db.session import get_session_factory
from app.graphs.research_analysis_graph import create_postgres_checkpointer
from app.logging_config import configure_logging
from app.services.run_service import ensure_default_workspace

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    init_tracing(settings)

    session_factory = get_session_factory(settings)
    app.state.session_factory = session_factory

    db = session_factory()
    try:
        ensure_default_workspace(db)
    except Exception:
        logger.warning(
            "Could not ensure default workspace at startup (is the DB reachable?)", exc_info=True
        )
    finally:
        db.close()

    try:
        PineconeClient(settings).ensure_index()
    except Exception:
        logger.warning(
            "Could not ensure Pinecone index at startup (check PINECONE_API_KEY)", exc_info=True
        )

    try:
        checkpointer = create_postgres_checkpointer(settings.database_url)
        checkpointer.setup()
        app.state.checkpointer = checkpointer
    except Exception:
        logger.warning(
            "Could not set up the LangGraph Postgres checkpointer — budget-approval resume won't "
            "work until the DB is reachable.",
            exc_info=True,
        )
        app.state.checkpointer = None

    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Market Research Agent API", lifespan=lifespan)
    app.include_router(health.router)
    app.include_router(discovery.router)
    app.include_router(selection.router)
    app.include_router(research.router)
    app.include_router(briefing.router)
    return app


app = create_app()
