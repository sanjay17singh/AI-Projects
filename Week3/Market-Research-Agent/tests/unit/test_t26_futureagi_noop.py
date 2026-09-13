"""T26 (+, supplementary): init_futureagi_tracing() no-ops without raising
when disabled, when credentials are missing, and when the optional
'futureagi' dependency group isn't importable — mirrors T25's contract for
init_tracing(). Also covers the real observed behavior once live-tested: with
the optional packages installed and *any* string values for FI_API_KEY/
FI_SECRET_KEY, register() succeeds without raising or validating them over
the network (spans are exported asynchronously) — same contract LangSmith's
init_tracing() has."""

import builtins

import pytest

from app.clients.futureagi_client import init_futureagi_tracing
from app.config import Settings


def test_noops_when_disabled():
    settings = Settings(openai_api_key="test-key", futureagi_enabled=False, fi_api_key="fi-key")
    assert init_futureagi_tracing(settings) is False


def test_noops_when_enabled_but_no_keys():
    settings = Settings(openai_api_key="test-key", futureagi_enabled=True)
    assert init_futureagi_tracing(settings) is False


def test_noops_when_sdk_not_importable(monkeypatch):
    """Forces the ImportError fallback path deterministically, regardless of
    whether the optional 'futureagi' dependency group happens to be
    installed in whatever environment runs this test."""
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("fi_instrumentation") or name.startswith("traceai_langchain"):
            raise ImportError(f"simulated missing optional dependency: {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    settings = Settings(
        openai_api_key="test-key",
        futureagi_enabled=True,
        fi_api_key="fi-key",
        fi_secret_key="fi-secret",
    )
    assert init_futureagi_tracing(settings) is False


def test_enables_when_keyed_and_sdk_installed():
    """Skips cleanly if the optional group isn't installed in this
    environment — mirrors T17/T18's optional-Postgres skip pattern. Where it
    does run, this is real, live-verified behavior: register()/instrument()
    do not validate FI_API_KEY/FI_SECRET_KEY synchronously, so even
    placeholder values succeed here — a bad key only fails silently later,
    when spans are actually exported."""
    pytest.importorskip("fi_instrumentation")
    pytest.importorskip("traceai_langchain")

    settings = Settings(
        openai_api_key="test-key",
        futureagi_enabled=True,
        fi_api_key="placeholder-key",
        fi_secret_key="placeholder-secret",
    )
    assert init_futureagi_tracing(settings) is True
