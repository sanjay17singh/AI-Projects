"""Thin requests-based wrapper, one function per FastAPI endpoint. Streamlit
pages never build a URL or call `requests` directly — this is the seam."""

import os

import requests
import streamlit as st


def _base_url() -> str:
    try:
        return st.secrets["BACKEND_BASE_URL"]
    except Exception:  # noqa: BLE001 — st.secrets raises if no secrets.toml exists
        return os.environ.get("BACKEND_BASE_URL", "http://localhost:8000")


def create_discovery_run(payload: dict) -> dict:
    r = requests.post(f"{_base_url()}/api/v1/discovery/runs", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


def get_discovery_run(run_id: str) -> dict:
    r = requests.get(f"{_base_url()}/api/v1/discovery/runs/{run_id}", timeout=30)
    r.raise_for_status()
    return r.json()


def select_competitors(run_id: str, candidate_ids: list[str]) -> dict:
    r = requests.post(
        f"{_base_url()}/api/v1/discovery/runs/{run_id}/selection",
        json={"competitor_candidate_ids": candidate_ids},
        timeout=30,
    )
    if r.status_code == 422:
        raise ValueError(r.json().get("detail", "Invalid selection"))
    r.raise_for_status()
    return r.json()


def get_research_status(run_id: str) -> dict:
    r = requests.get(f"{_base_url()}/api/v1/research/runs/{run_id}/status", timeout=30)
    r.raise_for_status()
    return r.json()


def approve_budget(run_id: str, new_budget_usd_limit: float) -> dict:
    r = requests.post(
        f"{_base_url()}/api/v1/research/runs/{run_id}/approve-budget",
        json={"new_budget_usd_limit": new_budget_usd_limit},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def get_briefing(run_id: str) -> dict | None:
    r = requests.get(f"{_base_url()}/api/v1/briefing/runs/{run_id}", timeout=30)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


def export_briefing(run_id: str, fmt: str) -> bytes:
    r = requests.get(f"{_base_url()}/api/v1/briefing/runs/{run_id}/export/{fmt}", timeout=30)
    r.raise_for_status()
    return r.content
