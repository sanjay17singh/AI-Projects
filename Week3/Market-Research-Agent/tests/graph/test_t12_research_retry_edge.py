"""T12 (+): a transient research failure on attempt 1 succeeds via the retry
edge on attempt 2."""

from app.graphs.edges import edge_research_retry


def test_failed_competitor_with_retries_left_is_resent():
    state = {
        "research_results": [{"competitor_id": "c1", "failed": True}],
        "retry_counts": {"c1": 0},
        "max_retries_per_competitor": 2,
        "competitors": [{"id": "c1", "name": "Acme"}],
    }
    sends = edge_research_retry(state)
    assert sends is not None
    assert len(sends) == 1
    assert sends[0].node == "web_research_node"
    assert sends[0].arg["_target_competitor"]["id"] == "c1"


def test_succeeded_competitor_on_retry_is_not_resent():
    state = {
        "research_results": [
            {"competitor_id": "c1", "failed": True},
            {"competitor_id": "c1", "failed": False},  # latest attempt succeeded
        ],
        "retry_counts": {"c1": 1},
        "max_retries_per_competitor": 2,
        "competitors": [{"id": "c1", "name": "Acme"}],
    }
    assert edge_research_retry(state) is None


def test_exhausted_retries_are_not_resent():
    state = {
        "research_results": [{"competitor_id": "c1", "failed": True}],
        "retry_counts": {"c1": 2},
        "max_retries_per_competitor": 2,
        "competitors": [{"id": "c1", "name": "Acme"}],
    }
    assert edge_research_retry(state) is None
