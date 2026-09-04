"""Smoke tests for every Streamlit page: each must render without an unhandled
exception, whether or not the FastAPI backend is reachable. Pages that call
the API are expected to degrade to st.error()/st.stop(), not crash — this
verifies that contract holds for real using Streamlit's AppTest harness
(no live API server needed).
"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

PAGES = [
    str(REPO_ROOT / "app/ui/app_pages/dashboard.py"),
    str(REPO_ROOT / "app/ui/app_pages/new_evaluation.py"),
    str(REPO_ROOT / "app/ui/app_pages/run_details.py"),
    str(REPO_ROOT / "app/ui/app_pages/human_review.py"),
    str(REPO_ROOT / "app/ui/app_pages/final_report.py"),
    str(REPO_ROOT / "app/ui/app_pages/scenario_library.py"),
]


@pytest.mark.parametrize("page_path", PAGES)
def test_page_renders_without_unhandled_exception(page_path, monkeypatch):
    monkeypatch.setenv("AGENTGATE_API_URL", "http://127.0.0.1:1")  # guaranteed unreachable
    at = AppTest.from_file(page_path, default_timeout=10)
    at.run()
    assert not at.exception, f"{page_path} raised: {[str(e) for e in at.exception]}"


def test_scenario_library_shows_all_40_scenarios(monkeypatch):
    at = AppTest.from_file(str(REPO_ROOT / "app/ui/app_pages/scenario_library.py"), default_timeout=10)
    at.run()
    assert not at.exception
    metric_values = {m.label: m.value for m in at.metric}
    assert metric_values["Total scenarios"] == "40"
    assert metric_values["Adversarial"] == "16"
    assert metric_values["Benign"] == "16"
    assert metric_values["Resilience"] == "8"
