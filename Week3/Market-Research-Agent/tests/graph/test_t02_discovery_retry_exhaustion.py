"""T02 (-): You.com timeout/HTTPError causes the discovery graph to retry,
then fail cleanly after max_retries."""

import uuid

from app.clients.youcom_client import YouComClientError
from app.graphs.discovery_graph import build_discovery_graph
from app.schemas.discovery import NormalizedRequest, SearchQueryList
from tests.fixtures.fake_llm import FakeChatModel


class AlwaysFailingYouCom:
    def search_web(self, query, category, count=10):
        raise YouComClientError("simulated timeout")


def test_discovery_graph_retries_then_fails_cleanly(settings, db_session_factory, monkeypatch):
    fake_model = FakeChatModel(
        {
            NormalizedRequest: NormalizedRequest(
                target_company_name="Acme",
                industry="CRM",
                geography="NA",
                customer_segment="SMB",
                news_window_days=60,
            ),
            SearchQueryList: SearchQueryList(queries=["acme competitors"]),
        }
    )
    monkeypatch.setattr(
        "app.agents.discovery_agent.get_chat_model", lambda settings, fast=False: fake_model
    )

    graph = build_discovery_graph(settings, db_session_factory, youcom_client=AlwaysFailingYouCom())

    initial_state = {
        "run_id": str(uuid.uuid4()),
        "workspace_id": str(uuid.uuid4()),
        "target_company_name": "Acme",
        "news_window_days": 60,
        "retry_count": 0,
        "max_retries": 2,
        "errors": [],
    }
    result = graph.invoke(initial_state, config={"recursion_limit": 50})

    assert result["status"] == "discovery_failed"
    assert result["retry_count"] == 2  # exhausted max_retries
    assert result["errors"]
    # generate_search_queries is invoked once per attempt: 1 initial + 2 retries = 3
    assert fake_model.structured_runnables[SearchQueryList].call_count == 3
