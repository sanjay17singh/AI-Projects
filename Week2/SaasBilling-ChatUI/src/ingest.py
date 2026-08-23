"""Chunk + embed the knowledge base and upsert into the Pinecone dense index.

Run with: uv run python src/ingest.py
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

from retrieval import EMBEDDING_DIMENSION, EMBEDDING_MODEL, _pinecone_index_name, get_chunked_documents


def _ensure_index(pc, index_name: str) -> None:
    from pinecone import ServerlessSpec

    existing = {idx["name"] for idx in pc.list_indexes()}
    if index_name in existing:
        return

    cloud = os.environ.get("PINECONE_CLOUD", "aws")
    region = os.environ.get("PINECONE_REGION", "us-east-1")
    print(f"Creating Pinecone index '{index_name}' ({cloud}/{region}, dim={EMBEDDING_DIMENSION})...")
    pc.create_index(
        name=index_name,
        dimension=EMBEDDING_DIMENSION,
        metric="cosine",
        spec=ServerlessSpec(cloud=cloud, region=region),
    )


def main() -> None:
    load_dotenv()

    if not os.environ.get("OPENAI_API_KEY") or not os.environ.get("PINECONE_API_KEY"):
        print("OPENAI_API_KEY and PINECONE_API_KEY must be set (see .env.example). Aborting.", file=sys.stderr)
        sys.exit(1)

    from langchain_openai import OpenAIEmbeddings
    from langchain_pinecone import PineconeVectorStore
    from pinecone import Pinecone

    index_name = _pinecone_index_name()
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    _ensure_index(pc, index_name)

    chunks = list(get_chunked_documents())
    print(f"Loaded and chunked {len(chunks)} document chunks from data/.")

    # chunk_id (assigned in chunk_documents) is deterministic and shared with the in-memory
    # BM25 corpus, so re-running is a safe idempotent upsert and dense/BM25 results can be
    # matched up later for the retrieval-transparency view.
    ids = [chunk.metadata["chunk_id"] for chunk in chunks]

    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
    store = PineconeVectorStore(index_name=index_name, embedding=embeddings)
    store.add_documents(chunks, ids=ids)

    print(f"Upserted {len(chunks)} chunks into Pinecone index '{index_name}'.")


if __name__ == "__main__":
    main()
