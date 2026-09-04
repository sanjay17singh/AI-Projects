from app.config import Settings
from app.tracing.langsmith import get_tracing_callbacks, tracing_enabled


def test_tracing_disabled_by_default():
    settings = Settings(langsmith_tracing=False, langsmith_api_key="")
    assert tracing_enabled(settings) is False
    assert get_tracing_callbacks(settings) == []


def test_tracing_disabled_when_flag_set_but_no_api_key():
    settings = Settings(langsmith_tracing=True, langsmith_api_key="")
    assert tracing_enabled(settings) is False
    assert get_tracing_callbacks(settings) == []


def test_tracing_enabled_returns_a_callback_when_key_is_valid(monkeypatch):
    import app.tracing.langsmith as module

    monkeypatch.setattr(module, "_build_validated_client", lambda key, project: object())
    settings = Settings(langsmith_tracing=True, langsmith_api_key="fake-key-for-test")
    callbacks = get_tracing_callbacks(settings)
    assert len(callbacks) == 1


def test_tracing_disabled_when_api_key_cannot_ingest(monkeypatch):
    """The exact bug this guards against: a key that can authenticate for some
    endpoints (e.g. listing projects) but can't actually ingest a run through
    LangChainTracer's multipart endpoint must still disable tracing up front,
    not attach a tracer that then spams 401s from a background thread on every
    single LLM call.
    """
    import app.tracing.langsmith as module

    monkeypatch.setattr(module, "_build_validated_client", lambda key, project: None)
    settings = Settings(langsmith_tracing=True, langsmith_api_key="invalid-key")
    assert get_tracing_callbacks(settings) == []


def test_validated_client_is_built_explicitly_not_from_environment(monkeypatch):
    """LangChainTracer falls back to its own os.environ-based Client() if none is
    passed in — AgentGate must always pass an explicit client built from its own
    Settings, since LANGSMITH_API_KEY is never written into the process
    environment (it only exists inside the app's Settings object).
    """
    import app.tracing.langsmith as module

    captured = {}

    class _FakeClient:
        def __init__(self, api_key):
            captured["api_key"] = api_key

    def fake_validate_ingest(client, project):
        return None

    monkeypatch.setattr("langsmith.Client", _FakeClient)
    monkeypatch.setattr(module, "_validate_ingest", fake_validate_ingest)
    module._build_validated_client.cache_clear()

    client = module._build_validated_client("explicit-key-from-settings", "proj")
    assert captured["api_key"] == "explicit-key-from-settings"
    assert isinstance(client, _FakeClient)


def test_build_validated_client_result_is_cached(monkeypatch):
    import app.tracing.langsmith as module

    module._build_validated_client.cache_clear()
    call_count = 0

    class _FakeClient:
        def __init__(self, api_key):
            nonlocal call_count
            call_count += 1

    monkeypatch.setattr("langsmith.Client", _FakeClient)
    monkeypatch.setattr(module, "_validate_ingest", lambda client, project: None)
    module._build_validated_client("same-key", "proj")
    module._build_validated_client("same-key", "proj")
    assert call_count == 1


def test_get_tracing_callbacks_never_raises_even_if_langsmith_broken(monkeypatch):
    import sys

    import app.tracing.langsmith as module

    settings = Settings(langsmith_tracing=True, langsmith_api_key="fake-key-for-test")
    monkeypatch.setattr(module, "tracing_enabled", lambda s=None: True)
    monkeypatch.setattr(module, "_build_validated_client", lambda key, project: object())

    class _BrokenTracerModule:
        def __getattr__(self, name):
            raise RuntimeError("simulated broken langsmith install")

    monkeypatch.setitem(sys.modules, "langchain_core.tracers", _BrokenTracerModule())
    callbacks = module.get_tracing_callbacks(settings)
    assert callbacks == []
