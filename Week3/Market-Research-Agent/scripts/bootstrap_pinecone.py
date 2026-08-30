#!/usr/bin/env python
"""Idempotent: creates the Pinecone index (from PINECONE_INDEX_NAME) if it
doesn't already exist. Safe to run repeatedly — the app also calls this at
startup, so running it manually is mostly useful for a first-time check that
PINECONE_API_KEY is valid before starting the full app."""

from app.clients.pinecone_client import PineconeClient
from app.config import get_settings


def main() -> None:
    settings = get_settings()
    client = PineconeClient(settings)
    client.ensure_index()
    print(f"Pinecone index '{settings.pinecone_index_name}' is ready.")


if __name__ == "__main__":
    main()
