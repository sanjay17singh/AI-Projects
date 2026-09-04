"""One-time (idempotent) setup of the LangGraph Postgres checkpoint tables.

Run after `alembic upgrade head`:
    uv run python scripts/setup_checkpointer.py
"""

from app.db.checkpointer import setup_checkpoint_tables

if __name__ == "__main__":
    setup_checkpoint_tables()
    print("LangGraph checkpoint tables ready.")
