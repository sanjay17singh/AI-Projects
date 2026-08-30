"""T16 (-): POST selection with 2 or 4 candidate IDs returns 422 and does not
persist a competitor_selections row."""

import pytest
from fastapi.testclient import TestClient

from app.db.models import CompetitorSelection
from app.schemas.discovery import CompetitorCandidate
from app.services import discovery_service, run_service


@pytest.fixture
def client(db_session_factory, monkeypatch):
    monkeypatch.setattr("app.api.main.get_session_factory", lambda settings: db_session_factory)
    monkeypatch.setattr(
        "app.clients.pinecone_client.PineconeClient.ensure_index", lambda self: None
    )

    from app.api.main import create_app

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def run_with_five_candidates(db_session_factory):
    db = db_session_factory()
    workspace = run_service.ensure_default_workspace(db)
    from app.schemas.discovery import DiscoveryRequest

    run = run_service.create_run(
        db, workspace.id, DiscoveryRequest(target_company_name="Acme"), 5.0
    )
    candidates = [
        CompetitorCandidate(
            company_name=f"Co{i}",
            match_score=0.5,
            classification="direct",
            explanation="e",
            source_urls=[],
        )
        for i in range(5)
    ]
    rows = discovery_service.persist_candidates(db, run.id, candidates)
    candidate_ids = [str(r.id) for r in rows]
    run_id = str(run.id)
    db.close()
    return run_id, candidate_ids


def test_selection_with_two_ids_returns_422_and_persists_nothing(
    client, run_with_five_candidates, db_session_factory
):
    run_id, candidate_ids = run_with_five_candidates

    response = client.post(
        f"/api/v1/discovery/runs/{run_id}/selection",
        json={"competitor_candidate_ids": candidate_ids[:2]},
    )

    assert response.status_code == 422

    db = db_session_factory()
    count = db.query(CompetitorSelection).count()
    db.close()
    assert count == 0


def test_selection_with_four_ids_returns_422(client, run_with_five_candidates):
    run_id, candidate_ids = run_with_five_candidates

    response = client.post(
        f"/api/v1/discovery/runs/{run_id}/selection",
        json={"competitor_candidate_ids": candidate_ids[:4]},
    )

    assert response.status_code == 422


def test_selection_with_exactly_three_ids_succeeds(client, run_with_five_candidates, monkeypatch):
    # Prevent the background task from actually building the research graph
    # (would require real OpenAI/Pinecone clients) — we're only testing the
    # validation + persistence path here.
    monkeypatch.setattr(
        "app.api.routers.selection._run_research_analysis_graph", lambda *a, **kw: None
    )

    run_id, candidate_ids = run_with_five_candidates
    response = client.post(
        f"/api/v1/discovery/runs/{run_id}/selection",
        json={"competitor_candidate_ids": candidate_ids[:3]},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "research_running"
