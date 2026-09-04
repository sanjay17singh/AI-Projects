"""Optional LangSmith development tracing with redaction, off by default.

The application must work identically whether LangSmith is configured,
misconfigured, or entirely down — every function here degrades to a no-op on
any failure instead of raising.
"""

import datetime
import uuid
from functools import lru_cache

import structlog
from langchain_core.messages import BaseMessage

from app.audit.redaction import redact_text
from app.config import Settings, get_settings

logger = structlog.get_logger(__name__)


def tracing_enabled(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    return bool(settings.langsmith_tracing and settings.langsmith_api_key)


def _validate_ingest(client, project: str) -> None:
    """Exercises the exact `multipart_ingest` code path LangChainTracer uses in
    the background to upload traces. A key can pass a plain read-only check
    (e.g. listing projects) while still lacking permission for this endpoint —
    that mismatch is exactly what let an invalid key slip through silently and
    spam 401s from a background thread on every traced call. Raises on failure;
    callers decide what "invalid" means.
    """
    trace_id = uuid.uuid4()
    dotted_order = f"{datetime.datetime.now(datetime.UTC):%Y%m%dT%H%M%S%f}Z{trace_id}"
    client.multipart_ingest(
        create=[
            {
                "id": str(trace_id),
                "session_name": project,
                "name": "agentgate-tracing-auth-check",
                "run_type": "chain",
                "dotted_order": dotted_order,
                "trace_id": str(trace_id),
                "inputs": {},
                "outputs": {},
            }
        ]
    )


@lru_cache(maxsize=8)
def _build_validated_client(api_key: str, project: str):
    """Builds a langsmith Client explicitly from our own Settings — never from
    langsmith's own os.environ auto-detection, which is what LangChainTracer
    falls back to if no client is passed in, and which silently picks up
    nothing (or a stale key) since AgentGate's Settings never writes
    LANGSMITH_API_KEY into the process environment. Returns None (cached) if
    the key can't actually ingest a run, so a bad key is checked once per
    process, not on every single LLM call.
    """
    try:
        from langsmith import Client

        client = Client(api_key=api_key)
        _validate_ingest(client, project)
        return client
    except Exception as exc:  # noqa: BLE001 - any failure here means "don't trace", not "crash"
        logger.warning("langsmith_auth_check_failed", project=project, error=str(exc))
        return None


def _redact_message(message: BaseMessage) -> BaseMessage:
    if isinstance(message.content, str):
        redacted = message.copy()
        redacted.content = redact_text(message.content)
        return redacted
    return message


def get_tracing_callbacks(settings: Settings | None = None) -> list:
    """Returns a redacting LangSmith tracer callback, or [] if tracing is disabled
    or LangSmith can't be initialized — never raises.
    """
    settings = settings or get_settings()
    if not tracing_enabled(settings):
        return []
    client = _build_validated_client(settings.langsmith_api_key, settings.langsmith_project)
    if client is None:
        return []
    try:
        from langchain_core.tracers import LangChainTracer

        class RedactingTracer(LangChainTracer):
            def on_chat_model_start(self, serialized, messages, **kwargs):
                redacted = [[_redact_message(m) for m in batch] for batch in messages]
                return super().on_chat_model_start(serialized, redacted, **kwargs)

            def on_llm_start(self, serialized, prompts, **kwargs):
                return super().on_llm_start(serialized, [redact_text(p) for p in prompts], **kwargs)

            def on_tool_start(self, serialized, input_str, **kwargs):
                return super().on_tool_start(serialized, redact_text(input_str), **kwargs)

        return [RedactingTracer(client=client, project_name=settings.langsmith_project)]
    except Exception as exc:  # noqa: BLE001 - LangSmith must never crash the app; degrade to no-op on any failure
        logger.warning("langsmith_unavailable", error=str(exc))
        return []
