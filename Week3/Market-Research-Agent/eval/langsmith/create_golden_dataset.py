#!/usr/bin/env python
"""Creates/upserts the `market-research-golden` LangSmith dataset from
eval/datasets/golden_scenarios.jsonl, tagging every example with a
`gold_version` metadata field. Idempotent — safe to re-run; only inserts
examples that don't already exist by scenario_id.

See eval/README.md before running.
"""

import argparse
from pathlib import Path

from dotenv import load_dotenv

# Must happen before `from langsmith import Client` — see the matching
# comment in eval/run_discovery_eval.py.
load_dotenv()

from langsmith import Client  # noqa: E402

from eval.schemas.eval_models import GoldenScenario  # noqa: E402

DATASET_NAME = "market-research-golden"
DATASET_PATH = Path(__file__).parent.parent / "datasets" / "golden_scenarios.jsonl"


def load_scenarios(path: Path = DATASET_PATH) -> list[GoldenScenario]:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found — run eval/datasets/generate_golden_dataset.py first."
        )
    scenarios = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                scenarios.append(GoldenScenario.model_validate_json(line))
    return scenarios


def ensure_dataset(client: Client, scenarios: list[GoldenScenario]) -> None:
    if not client.has_dataset(dataset_name=DATASET_NAME):
        client.create_dataset(
            dataset_name=DATASET_NAME,
            description="Market Research Agent 60-scenario Golden Dataset.",
        )

    existing = {
        ex.metadata.get("scenario_id")
        for ex in client.list_examples(dataset_name=DATASET_NAME)
        if ex.metadata
    }

    new_examples = []
    for scenario in scenarios:
        scenario_id = scenario.inputs.scenario_id
        if scenario_id in existing:
            continue
        new_examples.append(
            {
                "inputs": scenario.inputs.model_dump(mode="json"),
                "outputs": scenario.reference_outputs.model_dump(mode="json"),
                "metadata": {
                    "scenario_id": scenario_id,
                    "case_type": scenario.metadata.case_type,
                    "difficulty": scenario.metadata.difficulty,
                    "primary_metric": scenario.metadata.primary_metric,
                    "gold_version": scenario.metadata.gold_version,
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
    scenarios = load_scenarios(args.path)
    ensure_dataset(client, scenarios)


if __name__ == "__main__":
    main()
