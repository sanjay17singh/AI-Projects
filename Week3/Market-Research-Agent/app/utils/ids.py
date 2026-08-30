from uuid import UUID


def to_uuid(value: str | UUID) -> UUID:
    """Graph state carries ids as plain strings (JSON/checkpoint-friendly);
    SQLAlchemy's Uuid(as_uuid=True) columns require real UUID instances —
    this is the conversion boundary, used at every graph-node -> service call."""
    return value if isinstance(value, UUID) else UUID(value)
