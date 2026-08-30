"""T14 (+): 1 of 3 competitor branches fails permanently; the other 2 still
proceed to analysis (the orchestrator lets successful branches finish)."""

from app.graphs.edges import route_after_research_join


def test_one_permanent_failure_still_fans_out_analysis_for_the_rest():
    state = {
        "research_results": [
            {"competitor_id": "c1", "failed": False},
            {"competitor_id": "c2", "failed": True},
            {"competitor_id": "c3", "failed": False},
        ],
        "retry_counts": {"c2": 2},  # already exhausted retries for c2
        "max_retries_per_competitor": 2,
        "competitors": [
            {"id": "c1", "name": "A"},
            {"id": "c2", "name": "B"},
            {"id": "c3", "name": "C"},
        ],
    }
    result = route_after_research_join(state)
    assert isinstance(result, list)
    sent_ids = {s.arg["_target_competitor"]["id"] for s in result}
    assert sent_ids == {"c1", "c3"}
    assert all(s.node == "analysis_node" for s in result)


def test_all_permanently_failed_routes_to_fail_run():
    state = {
        "research_results": [
            {"competitor_id": "c1", "failed": True},
            {"competitor_id": "c2", "failed": True},
        ],
        "retry_counts": {"c1": 2, "c2": 2},
        "max_retries_per_competitor": 2,
        "competitors": [{"id": "c1", "name": "A"}, {"id": "c2", "name": "B"}],
    }
    assert route_after_research_join(state) == "fail_run"
