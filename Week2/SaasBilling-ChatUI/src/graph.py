"""LangGraph pipeline: classify -> retrieve -> generate -> score_and_decide -> save_memory.

Deliberately a linear, deterministic state graph (no AgentExecutor / RetrievalQA)
so the escalation logic is auditable rather than left to an LLM to improvise.
Every external call (OpenAI, Pinecone, Mem0) is wrapped so a failure degrades to
an escalation instead of raising into the UI.
"""

from __future__ import annotations

from typing import Optional, TypedDict

import confidence
import memory as memory_module
from langgraph.graph import END, START, StateGraph
from retrieval import hybrid_search
from schemas import BotResponse, ClassificationResult, CustomerMemory, RetrievedDoc

CLASSIFY_PROMPT = """You are classifying a SaaS billing support query into exactly one category.

Categories: refund, proration, payment_failure, cancellation, upgrade_downgrade, invoice_dispute, general_policy.

Customer context (background only, do not treat as fact about this specific query):
{memory_context}

Customer query:
{query}

Extract the category and any dollar amount explicitly mentioned in the query (null if none)."""

GENERATE_PROMPT = """You are a SaaS billing support assistant. Answer ONLY using the retrieved sources below.
Never fabricate specifics. If the sources don't clearly support a confident answer, set answer to null and
lower your confidence accordingly. Customer context is background only — never cite it as a source.

Confidence must reflect whether you are actually resolving THIS customer's specific situation, not just
whether you can recite a correct general policy. If the customer's message is vague or underspecified
(e.g. "something's wrong", "somehow changed", "do something about it") such that you cannot point to the
specific charge, error, or change they mean, that is a LOW-confidence case even if you can offer accurate
general background — do not let a well-supported general fact substitute for actually knowing what they need.
Customer context describes past, separate interactions — it can never raise your confidence about the
CURRENT query. Only the retrieved sources below, matched against what the customer actually asked this time,
may raise confidence.

Category: {category}

Customer context (background only, never a citation source):
{memory_context}

Retrieved sources (cite by the bracketed source_id):
{context}

Customer query:
{query}

Respond with: answer (grounded only in sources above, or null), citations (source_ids used), confidence (0-1),
category, dollar_amount (from the query, or null), escalate (your own judgment), escalation_reason (if escalate)."""

_classifier_llm = None
_generator_llm = None


def _get_classifier_llm():
    global _classifier_llm
    if _classifier_llm is None:
        from langchain_openai import ChatOpenAI

        _classifier_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0).with_structured_output(ClassificationResult)
    return _classifier_llm


def _get_generator_llm():
    global _generator_llm
    if _generator_llm is None:
        from langchain_openai import ChatOpenAI

        _generator_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0).with_structured_output(BotResponse)
    return _generator_llm


class GraphState(TypedDict, total=False):
    customer_id: str
    query: str
    memory: Optional[CustomerMemory]
    category: str
    dollar_amount: Optional[float]
    retrieved_docs: list[RetrievedDoc]
    retrieval_debug: dict
    response: BotResponse
    escalate: bool
    escalation_reason: Optional[str]
    system_error: Optional[str]


def load_memory_node(state: GraphState) -> dict:
    return {"memory": memory_module.get_customer_context(state["customer_id"])}


def classify_node(state: GraphState) -> dict:
    if state.get("system_error"):
        return {}
    try:
        memory_context = state["memory"].as_context_text() if state.get("memory") else "No prior context available."
        result: ClassificationResult = _get_classifier_llm().invoke(
            CLASSIFY_PROMPT.format(query=state["query"], memory_context=memory_context)
        )
        return {"category": result.category, "dollar_amount": result.dollar_amount}
    except Exception as e:  # OpenAI outage, bad response, etc.
        return {"system_error": f"classification_failed: {e}"}


def retrieve_node(state: GraphState) -> dict:
    if state.get("system_error"):
        return {}
    try:
        result = hybrid_search(state["query"], category=state.get("category"))
        return {
            "retrieved_docs": result["fused"],
            "retrieval_debug": {"dense": result["dense"], "bm25": result["bm25"]},
        }
    except Exception as e:  # Pinecone outage, index missing, etc.
        return {"system_error": f"retrieval_failed: {e}"}


def generate_node(state: GraphState) -> dict:
    if state.get("system_error"):
        return {}
    try:
        docs = state.get("retrieved_docs", [])
        context = (
            "\n\n".join(f"[{d.source_id}] ({d.category}/{d.source_type}) {d.text}" for d in docs)
            or "No relevant sources found."
        )
        memory_context = state["memory"].as_context_text() if state.get("memory") else "No prior context available."
        response: BotResponse = _get_generator_llm().invoke(
            GENERATE_PROMPT.format(
                category=state.get("category", "general_policy"),
                memory_context=memory_context,
                context=context,
                query=state["query"],
            )
        )
        return {"response": response}
    except Exception as e:
        return {"system_error": f"generation_failed: {e}"}


def score_and_decide_node(state: GraphState) -> dict:
    if state.get("system_error"):
        response = BotResponse(
            answer=None,
            citations=[],
            confidence=0.0,
            category=state.get("category", "general_policy"),
            dollar_amount=state.get("dollar_amount"),
            escalate=True,
            escalation_reason=f"System error: {state['system_error']}",
        )
        return {"response": response, "escalate": True, "escalation_reason": response.escalation_reason}

    response = state["response"]
    escalate, reason = confidence.decide(response, state.get("memory"))
    if escalate and response.answer is not None:
        # Never surface a sub-threshold or otherwise-escalated answer to the customer.
        response = response.model_copy(update={"answer": None})
    return {"response": response, "escalate": escalate, "escalation_reason": reason}


def save_memory_node(state: GraphState) -> dict:
    response = state.get("response")
    memory_module.save_turn_summary(
        customer_id=state["customer_id"],
        query=state["query"],
        category=state.get("category", "general_policy"),
        answer=response.answer if response else None,
        escalate=state.get("escalate", True),
        escalation_reason=state.get("escalation_reason"),
    )
    return {}


def build_graph():
    graph = StateGraph(GraphState)
    graph.add_node("load_memory", load_memory_node)
    graph.add_node("classify", classify_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("generate", generate_node)
    graph.add_node("score_and_decide", score_and_decide_node)
    graph.add_node("save_memory", save_memory_node)

    graph.add_edge(START, "load_memory")
    graph.add_edge("load_memory", "classify")
    graph.add_edge("classify", "retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", "score_and_decide")
    graph.add_edge("score_and_decide", "save_memory")
    graph.add_edge("save_memory", END)

    return graph.compile()


_compiled_graph = None


def get_compiled_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


def run(customer_id: str, query: str) -> dict:
    """Single entry point used by both app.py and eval/run_eval.py."""

    final_state: GraphState = get_compiled_graph().invoke(
        {"customer_id": customer_id, "query": query},
        config={"run_name": "billing_support_turn", "metadata": {"customer_id": customer_id}},
    )

    response: BotResponse = final_state["response"]
    return {
        "answer": response.answer,
        "citations": response.citations,
        "confidence": response.confidence,
        "category": response.category,
        "dollar_amount": response.dollar_amount,
        "escalate": final_state.get("escalate", True),
        "escalation_reason": final_state.get("escalation_reason"),
        "retrieved_docs": final_state.get("retrieved_docs", []),
        "retrieval_debug": final_state.get("retrieval_debug"),
        "memory": final_state.get("memory"),
    }
