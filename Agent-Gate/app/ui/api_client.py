"""Thin HTTP client the Streamlit UI uses to talk to the FastAPI backend.

Kept deliberately dumb (no caching of mutable state) — the UI always reflects
what's authoritative in Postgres via the API, never a stale local copy.
"""

import os

import httpx

BASE_URL = os.environ.get("AGENTGATE_API_URL", "http://localhost:8000")
TIMEOUT = 30.0


class ApiError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"{status_code}: {detail}")


def _request(method: str, path: str, **kwargs):
    try:
        response = httpx.request(method, f"{BASE_URL}{path}", timeout=TIMEOUT, **kwargs)
    except httpx.ConnectError as exc:
        raise ApiError(0, f"cannot reach AgentGate API at {BASE_URL}: {exc}") from exc
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except Exception:  # noqa: BLE001 - best-effort error detail extraction, response.text is the fallback
            detail = response.text
        raise ApiError(response.status_code, detail)
    return response.json()


def health() -> dict:
    return _request("GET", "/health")


def create_evaluation(
    *, tenant_id, change_type, title, diff_summary, raw_payload, created_by, idempotency_key
) -> dict:
    return _request(
        "POST",
        "/evaluations",
        json={
            "tenant_id": tenant_id,
            "change_type": change_type,
            "title": title,
            "diff_summary": diff_summary,
            "raw_payload": raw_payload,
            "created_by": created_by,
        },
        headers={"Idempotency-Key": idempotency_key},
    )


def list_evaluations() -> list:
    return _request("GET", "/evaluations")


def get_evaluation(run_id: str) -> dict:
    return _request("GET", f"/evaluations/{run_id}")


def get_evaluation_state(run_id: str) -> dict:
    return _request("GET", f"/evaluations/{run_id}/state")


def get_evaluation_scenarios(run_id: str) -> list:
    return _request("GET", f"/evaluations/{run_id}/scenarios")


def get_evaluation_findings(run_id: str) -> list:
    return _request("GET", f"/evaluations/{run_id}/findings")


def get_evaluation_report(run_id: str) -> dict | None:
    try:
        return _request("GET", f"/evaluations/{run_id}/report")
    except ApiError as exc:
        if exc.status_code == 404:
            return None
        raise


def get_pending_reviews() -> list:
    return _request("GET", "/human-reviews/pending")


def submit_human_decision(*, review_id, reviewer, decision, justification, idempotency_key=None) -> dict:
    return _request(
        "POST",
        "/human-decisions",
        json={
            "review_id": review_id,
            "reviewer": reviewer,
            "decision": decision,
            "justification": justification,
            "idempotency_key": idempotency_key,
        },
    )
