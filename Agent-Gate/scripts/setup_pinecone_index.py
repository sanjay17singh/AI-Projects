"""One-time (idempotent) creation of the Pinecone index AgentGate expects.

AgentGate never creates its own Pinecone index at runtime — querying or
upserting against a missing index is treated as ordinary Pinecone
unavailability (see app/retrieval/fallback.py) and degrades gracefully to the
local scenario catalog, which is why a missing index shows up as a
`pinecone_degraded` infrastructure issue rather than a crash. Run this once
per Pinecone project to actually enable semantic retrieval:

    uv run python scripts/setup_pinecone_index.py

Change PINECONE_CLOUD/PINECONE_REGION below if "aws"/"us-east-1" isn't
available on your Pinecone plan.
"""

from pinecone import Pinecone, ServerlessSpec

from app.config import get_settings
from app.retrieval.pinecone_client import EMBEDDING_DIMENSION

PINECONE_CLOUD = "aws"
PINECONE_REGION = "us-east-1"


def main() -> None:
    settings = get_settings()
    if not settings.pinecone_api_key:
        raise SystemExit("PINECONE_API_KEY is not set in .env — nothing to do.")

    client = Pinecone(api_key=settings.pinecone_api_key)

    if client.has_index(settings.pinecone_index_name):
        print(f"Index '{settings.pinecone_index_name}' already exists — nothing to do.")
        return

    client.create_index(
        name=settings.pinecone_index_name,
        dimension=EMBEDDING_DIMENSION,
        metric="cosine",
        spec=ServerlessSpec(cloud=PINECONE_CLOUD, region=PINECONE_REGION),
    )
    print(
        f"Created Pinecone index '{settings.pinecone_index_name}' "
        f"(dimension={EMBEDDING_DIMENSION}, metric=cosine, {PINECONE_CLOUD}/{PINECONE_REGION})."
    )
    print("It may take a minute to become ready before queries succeed.")


if __name__ == "__main__":
    main()
