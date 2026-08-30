from functools import partial

from langgraph.graph import END, StateGraph

from app.agents.discovery_agent import DiscoveryAgent
from app.clients.youcom_client import YouComClient
from app.config import Settings
from app.graphs.discovery_nodes import (
    DiscoveryDeps,
    call_youcom_search_node,
    generate_search_queries_node,
    handle_failure_node,
    normalize_request_node,
    persist_candidates_node,
    record_search_retry_node,
    score_and_classify_candidates_node,
)
from app.graphs.edges import edge_after_scoring, edge_after_search
from app.schemas.graph_state import DiscoveryGraphState


def build_discovery_graph(
    settings: Settings, session_factory, youcom_client: YouComClient | None = None
):
    client = youcom_client or YouComClient(settings.youcom_api_key, settings.youcom_base_url)
    agent = DiscoveryAgent(settings, client)
    deps = DiscoveryDeps(agent=agent, session_factory=session_factory)

    builder = StateGraph(DiscoveryGraphState)
    builder.add_node("normalize_request", partial(normalize_request_node, deps=deps))
    builder.add_node("generate_search_queries", partial(generate_search_queries_node, deps=deps))
    builder.add_node("call_youcom_search", partial(call_youcom_search_node, deps=deps))
    builder.add_node("record_search_retry", partial(record_search_retry_node, deps=deps))
    builder.add_node(
        "score_and_classify_candidates", partial(score_and_classify_candidates_node, deps=deps)
    )
    builder.add_node("persist_candidates", partial(persist_candidates_node, deps=deps))
    builder.add_node("handle_failure", partial(handle_failure_node, deps=deps))

    builder.set_entry_point("normalize_request")
    builder.add_edge("normalize_request", "generate_search_queries")
    builder.add_edge("generate_search_queries", "call_youcom_search")
    builder.add_conditional_edges("call_youcom_search", edge_after_search)
    builder.add_edge("record_search_retry", "generate_search_queries")
    builder.add_conditional_edges("score_and_classify_candidates", edge_after_scoring)
    builder.add_edge("persist_candidates", END)
    builder.add_edge("handle_failure", END)

    return builder.compile()
