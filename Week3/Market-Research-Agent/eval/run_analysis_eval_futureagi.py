#!/usr/bin/env python
"""Second, independent quality check for the Analysis and Verification
Agent, using Future AGI's evaluate("faithfulness", ...) instead of the
LangSmith LLM-as-judge in eval/evaluators/analysis_evaluators.py. Runs
alongside eval/run_analysis_eval.py by explicit product decision, not
instead of it.

Requires the optional `futureagi` uv dependency group
(`uv sync --group futureagi`) plus FI_API_KEY/FI_SECRET_KEY, and (like
run_analysis_eval.py) a real PINECONE_API_KEY — it seeds the same fixture
evidence into a scratch namespace and queries it back out through the real
retrieval path. See eval/README.md before running.

Programmatic groundedness (does every evidence_id actually resolve?) is
already covered by eval/evaluators/analysis_evaluators.py::groundedness and
is not duplicated here — this script is specifically the faithfulness
cross-check, using "faithfulness" because it's the one metric identifier
Future AGI's own docs show with the exact (output, context) shape this
project needs; see run_discovery_eval_futureagi.py's docstring for why
other, more semantically-precise metric names (e.g. "detect_hallucination")
were deliberately not guessed."""

import json
import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fi.evals import evaluate  # noqa: E402

from app.agents.analysis_agent import AnalysisVerificationAgent  # noqa: E402
from app.clients.futureagi_client import init_futureagi_tracing  # noqa: E402
from app.clients.openai_client import get_embeddings_model  # noqa: E402
from app.clients.pinecone_client import PineconeClient  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.schemas.common import ALL_PROFILE_CATEGORIES  # noqa: E402
from eval.run_analysis_eval import _seed_evidence  # noqa: E402

DATASET_PATH = Path(__file__).parent / "datasets" / "analysis_examples.json"
EVAL_WORKSPACE_ID = "eval-scratch-futureagi"


def _all_claims(profile: dict):
    for category in ALL_PROFILE_CATEGORIES:
        for claim in profile.get(category, []):
            yield category, claim


def main() -> None:
    settings = get_settings()
    init_futureagi_tracing(settings)

    pinecone = PineconeClient(settings)
    pinecone.ensure_index()
    embeddings = get_embeddings_model(settings)
    agent = AnalysisVerificationAgent(settings, pinecone)

    examples = json.loads(DATASET_PATH.read_text())
    scores = []
    for example in examples:
        inputs = example["inputs"]
        run_id = str(uuid.uuid4())
        competitor_id = str(uuid.uuid4())
        _seed_evidence(pinecone, embeddings, run_id, competitor_id, inputs["evidence"])

        profile = agent.analyze(
            workspace_id=EVAL_WORKSPACE_ID,
            run_id=run_id,
            competitor_id=competitor_id,
            competitor_name=inputs["competitor_name"],
        ).model_dump(mode="json")

        evidence_by_id = {e["evidence_id"]: e["text"] for e in inputs["evidence"]}
        for category, claim in _all_claims(profile):
            if claim.get("is_unsupported") or not claim.get("evidence_ids"):
                continue
            cited_text = "\n".join(
                evidence_by_id.get(eid, "")
                for eid in claim["evidence_ids"]
                if eid in evidence_by_id
            )
            if not cited_text:
                continue
            result = evaluate("faithfulness", output=claim["value"], context=cited_text)
            scores.append(result.score)
            print(
                f"{inputs['competitor_name']}/{category}: faithfulness={result.score:.2f} "
                f"passed={result.passed} — {result.reason}"
            )

    if scores:
        avg = sum(scores) / len(scores)
        print(f"\nAverage faithfulness across {len(scores)} claims: {avg:.2f}")
    else:
        print("No supported claims were produced to evaluate.")


if __name__ == "__main__":
    main()
