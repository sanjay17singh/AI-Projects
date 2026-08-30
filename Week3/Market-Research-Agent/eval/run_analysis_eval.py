#!/usr/bin/env python
"""Runs the Analysis and Verification Agent quality eval against real OpenAI
+ real Pinecone, using a small fixture set of pre-fetched evidence (not a
live web crawl, to keep this fast/cheap). See eval/README.md before running."""

import json
import uuid
from pathlib import Path

from dotenv import load_dotenv

# Must happen before `from langsmith import Client` is used below — see the
# matching comment in run_discovery_eval.py.
load_dotenv()

from langchain_core.documents import Document  # noqa: E402
from langsmith import Client, evaluate  # noqa: E402

from app.agents.analysis_agent import AnalysisVerificationAgent  # noqa: E402
from app.clients.openai_client import get_embeddings_model  # noqa: E402
from app.clients.pinecone_client import PineconeClient  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.utils.text_splitting import split_document  # noqa: E402
from eval.evaluators.analysis_evaluators import ANALYSIS_EVALUATORS  # noqa: E402

DATASET_NAME = "market-research-agent-analysis-examples"
DATASET_PATH = Path(__file__).parent / "datasets" / "analysis_examples.json"
EVAL_WORKSPACE_ID = "eval-scratch"


def ensure_dataset(client: Client) -> None:
    if client.has_dataset(dataset_name=DATASET_NAME):
        return
    client.create_dataset(dataset_name=DATASET_NAME, description="Analysis Agent eval examples")
    examples = json.loads(DATASET_PATH.read_text())
    client.create_examples(dataset_name=DATASET_NAME, examples=examples)


def _seed_evidence(
    pinecone: PineconeClient, embeddings, run_id: str, competitor_id: str, evidence: list[dict]
) -> None:
    """Upserts fixture evidence into a scratch Pinecone namespace, mirroring
    what the Web Research Agent would have stored, so the Analysis Agent's
    normal retrieval path can query it back out for real."""
    for item in evidence:
        chunks = split_document(
            Document(page_content=item["text"], metadata={"category": item["category"]})
        )
        vectors_text = [c.page_content for c in chunks]
        vectors = embeddings.embed_documents(vectors_text)
        payload = []
        for i, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True)):
            metadata = {
                "workspace_id": EVAL_WORKSPACE_ID,
                "run_id": run_id,
                "competitor_id": competitor_id,
                "evidence_id": item["evidence_id"],
                "category": item["category"],
                "source_type": "web",
                "canonical_url": item["url"],
                "title": "",
                "published_at": "",
                "fetched_at": "",
                "chunk_index": i,
                "provider": "eval-fixture",
                "text": chunk.page_content,
            }
            payload.append((f"{item['evidence_id']}_{i}", vector, metadata))
        pinecone.upsert(payload, namespace=EVAL_WORKSPACE_ID)


def make_target():
    settings = get_settings()
    pinecone = PineconeClient(settings)
    pinecone.ensure_index()
    embeddings = get_embeddings_model(settings)
    agent = AnalysisVerificationAgent(settings, pinecone)

    def target(inputs: dict) -> dict:
        run_id = str(uuid.uuid4())
        competitor_id = str(uuid.uuid4())
        _seed_evidence(pinecone, embeddings, run_id, competitor_id, inputs["evidence"])

        profile = agent.analyze(
            workspace_id=EVAL_WORKSPACE_ID,
            run_id=run_id,
            competitor_id=competitor_id,
            competitor_name=inputs["competitor_name"],
        )
        return profile.model_dump(mode="json")

    return target


def main() -> None:
    client = Client()
    ensure_dataset(client)

    results = evaluate(
        make_target(),
        data=DATASET_NAME,
        evaluators=ANALYSIS_EVALUATORS,
        experiment_prefix="analysis-agent",
        client=client,
    )
    print(results)


if __name__ == "__main__":
    main()
