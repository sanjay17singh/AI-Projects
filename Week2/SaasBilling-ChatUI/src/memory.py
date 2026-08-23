"""Mem0-backed per-customer long-term memory.

Distinct from the retrieval knowledge base: this module holds customer-specific
context (plan tier, past issues, prior escalations, preferences) that persists
across sessions. It is its own module so it can be disabled/mocked in the eval
harness, and so a Mem0 outage degrades to "no memory available" rather than
blocking a response.
"""

from __future__ import annotations

import os
from typing import Optional

from schemas import CustomerMemory, MemorySummary, PriorEscalation

MEMORY_ENABLED = True

_client = None
_summarizer = None


def _get_client():
    global _client
    if not MEMORY_ENABLED:
        return None
    if _client is None:
        from mem0 import MemoryClient

        api_key = os.environ.get("MEM0_API_KEY")
        if not api_key:
            return None
        _client = MemoryClient(api_key=api_key)
    return _client


def _get_summarizer():
    global _summarizer
    if _summarizer is None:
        from langchain_openai import ChatOpenAI

        _summarizer = ChatOpenAI(model="gpt-4o-mini", temperature=0).with_structured_output(MemorySummary)
    return _summarizer


def reset_customer_memory(customer_id: str) -> None:
    """Delete all stored memory for a customer. Mem0 Platform is a persistent hosted store —
    it does not clear itself between separate process runs, so anything that needs a clean
    baseline per run (the eval harness's shared customer, in particular) must call this first.

    Mem0's delete is asynchronous ("Delete in progress") — a read immediately after this call
    can still see the old data. Callers that need a guaranteed-clean read right after resetting
    should wait a beat (the eval harness does)."""

    client = _get_client()
    if client is None:
        return
    try:
        # Unlike search()/get_all(), delete_all() takes user_id as a top-level kwarg,
        # not wrapped in filters={} — passing filters here silently no-ops (400 from the API).
        client.delete_all(user_id=customer_id)
    except Exception:
        return


def get_customer_context(customer_id: str) -> Optional[CustomerMemory]:
    """Read prior context for this customer. Returns None on any failure or if disabled."""

    client = _get_client()
    if client is None:
        return None

    try:
        result = client.get_all(filters={"user_id": customer_id}, page_size=50)
        entries = result.get("results", []) if isinstance(result, dict) else result
    except Exception:
        return None

    memory = CustomerMemory()
    for entry in entries or []:
        text = entry.get("memory") or entry.get("text") or ""
        metadata = entry.get("metadata") or {}
        kind = metadata.get("kind")
        category = metadata.get("category")

        if kind == "plan_tier" and text:
            memory.plan_tier = text
        elif kind == "escalation":
            memory.prior_escalations.append(PriorEscalation(category=category or "unknown", reason=text))
        elif kind == "issue" and text:
            memory.prior_issues.append(text)
        elif kind == "preference" and text:
            memory.preferences.append(text)

    return memory


def save_turn_summary(
    customer_id: str,
    query: str,
    category: str,
    answer: Optional[str],
    escalate: bool,
    escalation_reason: Optional[str],
) -> None:
    """Summarize what's durable-worth-remembering from this turn and upsert to Mem0."""

    client = _get_client()
    if client is None:
        return

    try:
        if escalate:
            client.add(
                f"Escalated {category} issue: {escalation_reason or 'no reason given'}. Original query: {query}",
                user_id=customer_id,
                metadata={"kind": "escalation", "category": category},
            )

        summary = _get_summarizer().invoke(
            "Summarize only what's durable and worth remembering long-term about this customer "
            "from the support interaction below. Do not repeat the full transcript. If nothing is "
            "durable, set is_durable to false.\n\n"
            f"Customer query: {query}\n"
            f"Category: {category}\n"
            f"Bot answer (if any): {answer or '(none / escalated)'}\n"
            f"Escalated: {escalate}"
        )

        if not summary.is_durable:
            return

        if summary.issue_summary:
            client.add(
                summary.issue_summary,
                user_id=customer_id,
                metadata={"kind": "issue", "category": category},
            )
        if summary.plan_tier:
            client.add(
                summary.plan_tier,
                user_id=customer_id,
                metadata={"kind": "plan_tier"},
            )
        if summary.preference:
            client.add(
                summary.preference,
                user_id=customer_id,
                metadata={"kind": "preference"},
            )
    except Exception:
        # Mem0 failures must never block the response path.
        return
