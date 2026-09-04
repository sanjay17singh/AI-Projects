"""Hard security/authorization constants. Deterministic rules only — never LLM-tunable."""

REFUND_AUTO_APPROVAL_LIMIT = 50.0

UNTRUSTED_CONTENT_OPEN_TAG = "<untrusted_retrieved_content>"
UNTRUSTED_CONTENT_CLOSE_TAG = "</untrusted_retrieved_content>"
