"""Future AGI tracing is opt-in, runs alongside LangSmith (not instead of
it — see app/clients/langsmith_client.py), and must never block app startup.

Requires the optional `futureagi` uv dependency group (`fi-instrumentation-otel`
+ `traceai-langchain`; see pyproject.toml), which is NOT installed by default.
Imports are therefore deferred into the function body so a normal `uv sync`
(without that group) never fails just because this module gets imported.

Import shapes below (`fi_instrumentation.register`, `fi_instrumentation.fi_types.
ProjectType`, `traceai_langchain.LangChainInstrumentor`) are confirmed live
against a real FI_API_KEY/FI_SECRET_KEY as of ai-evaluation>=1.1.0 (an
earlier pin, ai-evaluation>=0.1.0, resolved to a broken 0.1.8 release whose
own code imported a `fi.testcases` module its `futureagi` dependency no
longer ships — bumped the floor once that was diagnosed). Note
`LangGraphInstrumentor` is NOT used here even though it was in an earlier
version of this module: the installed traceai_langchain package logs it as
deprecated and a no-op — LangChainInstrumentor alone now captures LangGraph
node/tool/LLM spans automatically.

Also confirmed live: register()/instrument() do not make a network call or
validate credentials synchronously — spans are exported asynchronously by a
BatchSpanProcessor, so (like LangSmith's init_tracing()) a bad key doesn't
raise here, it just means traces silently fail to upload later."""

import logging
import os

from app.config import Settings

logger = logging.getLogger(__name__)


def init_futureagi_tracing(settings: Settings) -> bool:
    """Returns True if Future AGI tracing was enabled, False if it no-op'd
    (disabled by config, credentials missing, or the optional packages
    aren't installed)."""
    if not settings.futureagi_enabled or not settings.fi_api_key or not settings.fi_secret_key:
        return False

    try:
        from fi_instrumentation import register
        from fi_instrumentation.fi_types import ProjectType
        from traceai_langchain import LangChainInstrumentor
    except ImportError:
        logger.warning(
            "FUTUREAGI_ENABLED=true but the optional 'futureagi' dependency group isn't "
            "installed — run `uv sync --group futureagi`. Skipping Future AGI tracing."
        )
        return False

    # register() reads FI_API_KEY/FI_SECRET_KEY from the environment, not as
    # constructor arguments — same pattern as init_tracing() setting
    # LANGCHAIN_API_KEY for LangChain's tracer to pick up.
    os.environ["FI_API_KEY"] = settings.fi_api_key
    os.environ["FI_SECRET_KEY"] = settings.fi_secret_key

    try:
        trace_provider = register(
            project_type=ProjectType.OBSERVE, project_name=settings.fi_project_name
        )
        LangChainInstrumentor().instrument(tracer_provider=trace_provider)
    except Exception:
        # Unlike LangSmith's init_tracing() (which only sets env vars and
        # cannot fail), register()/instrument() do real setup work — an
        # unreachable collector or bad key here must degrade to "no Future
        # AGI tracing," never crash app startup.
        logger.warning("Could not initialize Future AGI tracing", exc_info=True)
        return False

    return True
