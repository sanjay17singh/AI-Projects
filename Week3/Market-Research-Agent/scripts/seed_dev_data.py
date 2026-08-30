#!/usr/bin/env python
"""Optional: seeds the default workspace row for local dev. The app also does
this at startup, so this script is mostly useful for confirming DATABASE_URL
is reachable before starting the full app."""

from app.config import get_settings
from app.db.session import get_session_factory
from app.services.run_service import ensure_default_workspace


def main() -> None:
    settings = get_settings()
    session_factory = get_session_factory(settings)
    db = session_factory()
    try:
        workspace = ensure_default_workspace(db)
        print(f"Default workspace ready: id={workspace.id} name={workspace.name!r}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
