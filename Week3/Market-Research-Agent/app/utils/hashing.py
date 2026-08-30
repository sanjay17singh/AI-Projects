import hashlib
import re

_WHITESPACE_RE = re.compile(r"\s+")


def content_hash(text: str) -> str:
    """sha256 of whitespace-normalized text — catches near-identical refetches
    (different surrounding whitespace/newlines) as the same evidence."""
    normalized = _WHITESPACE_RE.sub(" ", text).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
