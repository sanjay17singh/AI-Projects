"""Stub replacing a LangChain chat model's `.with_structured_output(Model)`.
Keyed by the Pydantic model class so a single fake can back an agent that
calls with_structured_output() with different models across a run (e.g.
DiscoveryAgent: SearchQueryList then CandidateList)."""

from typing import Any


class _FakeStructuredRunnable:
    def __init__(self, result: Any):
        self._result = result
        self.call_count = 0
        self.last_messages = None

    def invoke(self, messages):
        self.last_messages = messages
        self.call_count += 1
        result = self._result
        if isinstance(result, list):
            index = min(self.call_count - 1, len(result) - 1)
            result = result[index]
        if isinstance(result, BaseException):
            raise result
        return result


class FakeChatModel:
    """results_by_model: {ModelClass: instance | list[instance] | Exception}"""

    def __init__(self, results_by_model: dict[type, Any] | None = None):
        self._results_by_model = results_by_model or {}
        self.structured_runnables: dict[type, _FakeStructuredRunnable] = {}

    def with_structured_output(self, model_cls: type) -> _FakeStructuredRunnable:
        # Memoized per model class so call_count accumulates correctly even
        # though real code calls get_chat_model(...).with_structured_output(X)
        # fresh on every node invocation (e.g. across retries).
        if model_cls not in self.structured_runnables:
            self.structured_runnables[model_cls] = _FakeStructuredRunnable(
                self._results_by_model.get(model_cls)
            )
        return self.structured_runnables[model_cls]
