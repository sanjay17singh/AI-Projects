from functools import partial

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, StateGraph
from psycopg_pool import ConnectionPool

from app.agents.analysis_agent import AnalysisVerificationAgent
from app.agents.web_research_agent import WebResearchAgent
from app.clients.pinecone_client import PineconeClient
from app.clients.search_client import SearchClient
from app.clients.serper_client import SerperClient
from app.clients.youcom_client import YouComClient
from app.config import Settings
from app.graphs.analysis_nodes import (
    analysis_join_node,
    analysis_node,
    compile_briefing_node,
    fail_run_node,
    finalize_run_node,
)
from app.graphs.edges import edge_budget_check, edge_coverage_check, route_after_research_join
from app.graphs.research_nodes import (
    ResearchDeps,
    gap_research_node,
    plan_research_node,
    request_budget_approval_node,
    research_join_node,
    web_research_node,
)
from app.schemas.graph_state import ResearchGraphState


def _to_psycopg_conninfo(database_url: str) -> str:
    """PostgresSaver/psycopg want a plain 'postgresql://...' DSN, not
    SQLAlchemy's 'postgresql+psycopg://...' driver-qualified URL."""
    return database_url.replace("postgresql+psycopg://", "postgresql://")


def create_postgres_checkpointer(database_url: str) -> PostgresSaver:
    """Long-lived checkpointer for the Research+Analysis graph — exists
    solely so a mid-run budget-approval pause can survive an HTTP request
    boundary (see plan decision #2). Call .setup() once (idempotent) before
    first use; the caller owns the pool's lifetime."""
    # autocommit=True is required by PostgresSaver.setup() (it runs
    # CREATE INDEX CONCURRENTLY, which cannot execute inside a transaction).
    pool = ConnectionPool(
        conninfo=_to_psycopg_conninfo(database_url),
        max_size=10,
        kwargs={"autocommit": True, "prepare_threshold": 0},
        open=True,
    )
    return PostgresSaver(pool)


def build_search_clients(settings: Settings) -> list[SearchClient]:
    """You.com is always included; Serper is added only when explicitly
    enabled AND a key is configured — either condition alone leaves it out,
    so a stray SERPER_API_KEY without SERPER_ENABLED=true never silently
    starts spending on a second provider."""
    clients: list[SearchClient] = [YouComClient(settings.youcom_api_key, settings.youcom_base_url)]
    if settings.serper_enabled and settings.serper_api_key:
        clients.append(SerperClient(settings.serper_api_key, settings.serper_base_url))
    return clients


def build_research_analysis_graph(
    settings: Settings,
    session_factory,
    search_clients: list[SearchClient] | None = None,
    pinecone_client: PineconeClient | None = None,
    checkpointer=None,
):
    clients = search_clients or build_search_clients(settings)
    pinecone = pinecone_client or PineconeClient(settings)
    web_research_agent = WebResearchAgent(settings, clients, pinecone)
    analysis_agent = AnalysisVerificationAgent(settings, pinecone)
    deps = ResearchDeps(
        web_research_agent=web_research_agent,
        analysis_agent=analysis_agent,
        session_factory=session_factory,
    )

    builder = StateGraph(ResearchGraphState)
    builder.add_node("plan_research", partial(plan_research_node, deps=deps))
    builder.add_node("request_budget_approval", partial(request_budget_approval_node, deps=deps))
    builder.add_node("web_research_node", partial(web_research_node, deps=deps))
    builder.add_node("research_join_node", partial(research_join_node, deps=deps))
    builder.add_node("analysis_node", partial(analysis_node, deps=deps))
    builder.add_node("analysis_join_node", partial(analysis_join_node, deps=deps))
    builder.add_node("gap_research_node", partial(gap_research_node, deps=deps))
    builder.add_node("compile_briefing", partial(compile_briefing_node, deps=deps))
    builder.add_node("finalize_run", partial(finalize_run_node, deps=deps))
    builder.add_node("fail_run", partial(fail_run_node, deps=deps))

    builder.set_entry_point("plan_research")
    builder.add_conditional_edges("plan_research", edge_budget_check)
    builder.add_conditional_edges("request_budget_approval", edge_budget_check)
    builder.add_edge("web_research_node", "research_join_node")
    builder.add_conditional_edges("research_join_node", route_after_research_join)
    builder.add_edge("analysis_node", "analysis_join_node")
    builder.add_edge("gap_research_node", "analysis_join_node")
    builder.add_conditional_edges("analysis_join_node", edge_coverage_check)
    builder.add_edge("compile_briefing", "finalize_run")
    builder.add_edge("finalize_run", END)
    builder.add_edge("fail_run", END)

    return builder.compile(checkpointer=checkpointer)
