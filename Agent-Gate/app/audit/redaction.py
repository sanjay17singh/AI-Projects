"""Secret/PII redaction applied before anything is persisted as Evidence,
sent to Pinecone, or sent to LangSmith. Separate from the deterministic
policy engine — this is about *storage/telemetry hygiene*, not authorization.
"""

import re

_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b\d{13,19}\b"), "[REDACTED_CARD_NUMBER]"),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[REDACTED_EMAIL]"),
    (re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"), "[REDACTED_PHONE]"),
    (re.compile(r"\b(sk|pk|rk)-[A-Za-z0-9]{10,}\b"), "[REDACTED_API_KEY]"),
]


def redact_text(text: str) -> str:
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def redact_value(value):
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return {k: redact_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_value(v) for v in value]
    return value
