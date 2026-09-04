"""Centralized OpenAI model configuration, bounded retries, and structured-output helper.

Every LLM call in AgentGate goes through this module so timeout/retry/model
policy lives in exactly one place. Structured-output calls are the only way
agents get LLM judgments back into typed Pydantic models — free-text parsing
is not used anywhere in the decision path.
"""

import openai
import tenacity
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.config import Settings, get_settings

DEFAULT_TIMEOUT_SECONDS = 30.0
MAX_ATTEMPTS = 3

RETRYABLE_EXCEPTIONS = (
    openai.APITimeoutError,
    openai.RateLimitError,
    openai.APIConnectionError,
    openai.InternalServerError,
)

class LLMUnavailableError(Exception):
    """Raised when bounded retries are exhausted against a transient OpenAI failure."""


def build_chat_model(
    settings: Settings | None = None,
    temperature: float = 0.0,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    callbacks: list | None = None,
) -> BaseChatModel:
    settings = settings or get_settings()
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key or "sk-not-configured",
        temperature=temperature,
        timeout=timeout,
        max_retries=0,  # retries are handled explicitly below, not silently by the SDK
        callbacks=callbacks or [],
    )


def call_structured[T: BaseModel](model: BaseChatModel, schema: type[T], messages: list) -> T:
    """Invoke `model` and parse the response into `schema`, with bounded retry on
    transient errors only. Never retries on invalid structured output produced by
    the model itself — that's a product/evaluation-system failure, not transient,
    and callers should handle ValueError explicitly.
    """
    structured_model = model.with_structured_output(schema, strict=True)

    retrying = tenacity.Retrying(
        stop=tenacity.stop_after_attempt(MAX_ATTEMPTS),
        wait=tenacity.wait_exponential(multiplier=1, min=1, max=10),
        retry=tenacity.retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        reraise=False,
    )
    try:
        for attempt in retrying:
            with attempt:
                return structured_model.invoke(messages)  # type: ignore[return-value]
    except tenacity.RetryError as exc:
        raise LLMUnavailableError(f"OpenAI call failed after {MAX_ATTEMPTS} attempts") from exc
    raise LLMUnavailableError("OpenAI call failed")
