#!/usr/bin/env python
"""Creates/upserts the `market-research-evidence` LangSmith dataset from
eval/datasets/frozen_evidence.jsonl, tagging every example with an
`evidence_version` metadata field. Same idempotent pattern as
create_golden_dataset.py — see eval/README.md before running.
"""

import argparse
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from langsmith import Client  # noqa: E402

from eval.schemas.eval_models import EvidenceRecord  # noqa: E402

DATASET_NAME = "market-research-evidence"
DATASET_PATH = Path(__file__).parent.parent / "datasets" / "frozen_evidence.jsonl"
EVIDENCE_VERSION = "evidence-v1"


def load_evidence(path: Path = DATASET_PATH) -> list[EvidenceRecord]:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found — run eval/datasets/generate_golden_dataset.py first."
        )
    records = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(EvidenceRecord.model_validate_json(line))
    return records


def ensure_dataset(client: Client, records: list[EvidenceRecord]) -> None:
    if not client.has_dataset(dataset_name=DATASET_NAME):
        client.create_dataset(
            dataset_name=DATASET_NAME,
            description="Market Research Agent Frozen Evidence Corpus.",
        )

    existing = {
        ex.metadata.get("evidence_id")
        for ex in client.list_examples(dataset_name=DATASET_NAME)
        if ex.metadata
    }

    new_examples = []
    for record in records:
        if record.evidence_id in existing:
            continue
        new_examples.append(
            {
                "inputs": {"evidence_id": record.evidence_id, "company": record.company},
                "outputs": record.model_dump(mode="json"),
                "metadata": {
                    "evidence_id": record.evidence_id,
                    "company": record.company,
                    "category": record.category,
                    "evidence_version": EVIDENCE_VERSION,
                },
            }
        )

    if new_examples:
        client.create_examples(dataset_name=DATASET_NAME, examples=new_examples)
    print(
        f"Dataset {DATASET_NAME!r}: {len(new_examples)} new example(s) added, "
        f"{len(existing)} already present."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=DATASET_PATH)
    args = parser.parse_args()

    client = Client()
    records = load_evidence(args.path)
    ensure_dataset(client, records)


if __name__ == "__main__":
    main()
