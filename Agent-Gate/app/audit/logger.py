"""Structured audit event logging — fail-closed by design.

Audit events are written directly and synchronously inside the same
transaction boundary as the business write they describe wherever possible.
If a write to audit_events fails, callers must treat that as a reason to
halt the run (fail closed), never swallow it and continue.
"""

import hashlib
import json
from typing import Any

from app.db.models import AuditEventModel
from app.db.session import SessionFactory


class AuditLogWriteError(Exception):
    """The audit_events write failed — the caller must fail closed, not proceed silently."""


def compute_state_hash(state: dict[str, Any]) -> str:
    payload = json.dumps(state, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def record_audit_event(
    session_factory: SessionFactory,
    *,
    run_id: str | None,
    actor: str,
    action: str,
    correlation_id: str,
    input_ref: str | None = None,
    output_ref: str | None = None,
    state_hash: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    try:
        with session_factory.session() as session:
            session.add(
                AuditEventModel(
                    run_id=run_id,
                    actor=actor,
                    action=action,
                    correlation_id=correlation_id,
                    input_ref=input_ref,
                    output_ref=output_ref,
                    state_hash=state_hash,
                    event_metadata=metadata or {},
                )
            )
            session.commit()
    except Exception as exc:
        raise AuditLogWriteError(f"failed to persist audit event '{action}': {exc}") from exc
