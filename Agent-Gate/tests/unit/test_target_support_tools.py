from app.agents.target_support.tools import ToolContext, build_target_tools
from app.policy.constants import UNTRUSTED_CONTENT_OPEN_TAG
from app.schemas.execution import RetrievedDocument


def _tools_for(mode: str, session_customer_id: str = "CUST-1001", docs=None):
    ctx = ToolContext(mode=mode, session_customer_id=session_customer_id, retrieved_documents=docs or [])
    tools = {t.name: t for t in build_target_tools(ctx)}
    return ctx, tools


def test_guarded_lookup_blocks_cross_customer_access():
    ctx, tools = _tools_for("guarded", session_customer_id="CUST-1001")
    result = tools["lookup_customer"].invoke({"customer_id": "CUST-1002"})
    assert "authorization_denied" in result
    assert ctx.call_log[-1].error is not None


def test_guarded_lookup_allows_own_account():
    ctx, tools = _tools_for("guarded", session_customer_id="CUST-1001")
    result = tools["lookup_customer"].invoke({"customer_id": "CUST-1001"})
    assert "Alice Kim" in result
    assert ctx.call_log[-1].error is None


def test_vulnerable_lookup_allows_cross_customer_access():
    ctx, tools = _tools_for("vulnerable", session_customer_id="CUST-1001")
    result = tools["lookup_customer"].invoke({"customer_id": "CUST-1002"})
    assert "Bob Nguyen" in result
    assert ctx.call_log[-1].error is None


def test_guarded_refund_blocks_above_limit_without_approval():
    ctx, tools = _tools_for("guarded", session_customer_id="CUST-1001")
    result = tools["issue_refund"].invoke({"customer_id": "CUST-1001", "amount": 500, "reason": "defective"})
    assert "approval_required" in result
    assert ctx.refund_ledger == []


def test_guarded_refund_allows_above_limit_with_approval_ticket():
    ctx, tools = _tools_for("guarded", session_customer_id="CUST-1001")
    result = tools["issue_refund"].invoke(
        {"customer_id": "CUST-1001", "amount": 500, "reason": "defective", "approval_ticket_id": "TCK-1"}
    )
    assert "issued" in result
    assert len(ctx.refund_ledger) == 1


def test_guarded_refund_allows_within_limit():
    ctx, tools = _tools_for("guarded", session_customer_id="CUST-1001")
    result = tools["issue_refund"].invoke({"customer_id": "CUST-1001", "amount": 15, "reason": "late delivery"})
    assert "issued" in result
    assert len(ctx.refund_ledger) == 1


def test_vulnerable_refund_allows_above_limit_without_approval():
    ctx, tools = _tools_for("vulnerable", session_customer_id="CUST-1001")
    result = tools["issue_refund"].invoke({"customer_id": "CUST-1001", "amount": 500, "reason": "urgent"})
    assert "issued" in result
    assert len(ctx.refund_ledger) == 1


def test_guarded_refund_blocks_cross_customer_even_within_limit():
    ctx, tools = _tools_for("guarded", session_customer_id="CUST-1001")
    result = tools["issue_refund"].invoke({"customer_id": "CUST-1002", "amount": 10, "reason": "x"})
    assert "authorization_denied" in result
    assert ctx.refund_ledger == []


def test_guarded_support_message_blocks_cross_customer():
    ctx, tools = _tools_for("guarded", session_customer_id="CUST-1001")
    result = tools["create_support_message"].invoke({"customer_id": "CUST-1002", "body": "hello"})
    assert "authorization_denied" in result
    assert ctx.messages_ledger == []


def test_guarded_search_wraps_untrusted_documents_with_tags():
    doc = RetrievedDocument(doc_id="d1", title="Refund FAQ", content="malicious instruction", trusted=False)
    _ctx, tools = _tools_for("guarded", docs=[doc])
    result = tools["search_knowledge_base"].invoke({"query": "refund policy"})
    assert UNTRUSTED_CONTENT_OPEN_TAG in result


def test_vulnerable_search_does_not_wrap_untrusted_documents():
    doc = RetrievedDocument(doc_id="d1", title="Refund FAQ", content="malicious instruction", trusted=False)
    _ctx, tools = _tools_for("vulnerable", docs=[doc])
    result = tools["search_knowledge_base"].invoke({"query": "refund policy"})
    assert UNTRUSTED_CONTENT_OPEN_TAG not in result
    assert "malicious instruction" in result


def test_trusted_documents_are_never_wrapped_even_in_guarded_mode():
    doc = RetrievedDocument(doc_id="d1", title="Return Policy", content="30 days", trusted=True)
    _ctx, tools = _tools_for("guarded", docs=[doc])
    result = tools["search_knowledge_base"].invoke({"query": "return policy"})
    assert UNTRUSTED_CONTENT_OPEN_TAG not in result
