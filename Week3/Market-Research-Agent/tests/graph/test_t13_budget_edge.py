"""T13 (+): projected cost over budget routes to request_budget_approval;
once approved, it routes to fan-out instead."""

from app.graphs.edges import edge_budget_check


def test_over_budget_and_not_approved_routes_to_approval():
    state = {
        "projected_cost_usd": 8.0,
        "actual_cost_usd": 0.0,
        "budget_usd_limit": 5.0,
        "approved": False,
        "competitors": [{"id": "c1", "name": "Acme"}],
    }
    assert edge_budget_check(state) == "request_budget_approval"


def test_over_budget_but_approved_routes_to_fan_out():
    state = {
        "projected_cost_usd": 8.0,
        "actual_cost_usd": 0.0,
        "budget_usd_limit": 5.0,
        "approved": True,
        "competitors": [{"id": "c1", "name": "Acme"}, {"id": "c2", "name": "Beta"}],
    }
    sends = edge_budget_check(state)
    assert isinstance(sends, list)
    assert len(sends) == 2
    assert all(s.node == "web_research_node" for s in sends)


def test_within_budget_routes_to_fan_out_without_approval():
    state = {
        "projected_cost_usd": 1.0,
        "actual_cost_usd": 0.0,
        "budget_usd_limit": 5.0,
        "approved": False,
        "competitors": [{"id": "c1", "name": "Acme"}],
    }
    sends = edge_budget_check(state)
    assert isinstance(sends, list)
    assert len(sends) == 1
