"""T25 (+): init_tracing() no-ops without raising when LANGCHAIN_API_KEY is
unset."""

from app.clients.langsmith_client import init_tracing
from app.config import Settings


def test_init_tracing_noops_without_key():
    settings = Settings(openai_api_key="test-key", langchain_api_key="")
    result = init_tracing(settings)
    assert result is False


def test_init_tracing_enables_when_key_and_flag_present():
    settings = Settings(
        openai_api_key="test-key", langchain_api_key="ls-key", langchain_tracing_v2=True
    )
    result = init_tracing(settings)
    assert result is True
