"""LangSmith tracing is opt-in and must never block app startup. init_tracing()
only sets the env vars LangChain's tracer reads; it makes no network call
itself, so it can't fail even with an invalid key — a bad key just means
traces silently fail to upload later, which is acceptable for an MVP."""

import os

from app.config import Settings


def init_tracing(settings: Settings) -> bool:
    """Returns True if tracing was enabled, False if it no-op'd (no key set)."""
    if not settings.langchain_api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        return False

    os.environ["LANGCHAIN_TRACING_V2"] = "true" if settings.langchain_tracing_v2 else "false"
    os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
    return settings.langchain_tracing_v2
