"""Verifies bounded retry behavior: transient OpenAI errors are retried a
bounded number of times and then surfaced as LLMUnavailableError; a
non-transient error (e.g. invalid structured output) is never retried.
"""

import httpx
import openai
import pytest
from pydantic import BaseModel

from app.llm import MAX_ATTEMPTS, LLMUnavailableError, call_structured


class _Schema(BaseModel):
    value: str


class _AlwaysTimesOutStructuredModel:
    def __init__(self):
        self.call_count = 0

    def invoke(self, messages):
        self.call_count += 1
        raise openai.APITimeoutError(request=httpx.Request("POST", "https://api.openai.com/v1/x"))


class _AlwaysTimesOutModel:
    def __init__(self):
        self.structured = _AlwaysTimesOutStructuredModel()

    def with_structured_output(self, schema, strict=True):
        return self.structured


class _SucceedsAfterTwoFailuresStructuredModel:
    def __init__(self):
        self.call_count = 0

    def invoke(self, messages):
        self.call_count += 1
        if self.call_count < 3:
            raise openai.APITimeoutError(request=httpx.Request("POST", "https://api.openai.com/v1/x"))
        return _Schema(value="ok")


class _SucceedsAfterTwoFailuresModel:
    def __init__(self):
        self.structured = _SucceedsAfterTwoFailuresStructuredModel()

    def with_structured_output(self, schema, strict=True):
        return self.structured


class _RaisesValueErrorStructuredModel:
    def __init__(self):
        self.call_count = 0

    def invoke(self, messages):
        self.call_count += 1
        raise ValueError("invalid structured output")


class _RaisesValueErrorModel:
    def __init__(self):
        self.structured = _RaisesValueErrorStructuredModel()

    def with_structured_output(self, schema, strict=True):
        return self.structured


def test_call_structured_raises_llm_unavailable_after_bounded_retries():
    model = _AlwaysTimesOutModel()
    with pytest.raises(LLMUnavailableError):
        call_structured(model, _Schema, [])
    assert model.structured.call_count == MAX_ATTEMPTS


def test_call_structured_succeeds_after_transient_failures_within_bound():
    model = _SucceedsAfterTwoFailuresModel()
    result = call_structured(model, _Schema, [])
    assert result.value == "ok"
    assert model.structured.call_count == 3


def test_call_structured_does_not_retry_non_transient_errors():
    model = _RaisesValueErrorModel()
    with pytest.raises(ValueError):
        call_structured(model, _Schema, [])
    assert model.structured.call_count == 1
