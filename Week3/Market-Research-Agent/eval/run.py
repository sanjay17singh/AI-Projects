#!/usr/bin/env python
"""CLI entry point for the Golden Dataset / Frozen Evidence Corpus release
evaluation. See eval/README.md.

    uv run python -m eval.run --mode frozen --repetitions 1
    uv run python -m eval.run --mode frozen --repetitions 3
    uv run python -m eval.run --dataset-version gold-v1 --evidence-version evidence-v1 \\
        --top-k 5 --repetitions 3

Exits non-zero when the release gate status is FAIL, so this can be wired
into CI later even though nothing does so yet.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DATASETS_DIR = Path(__file__).parent / "datasets"
GOLDEN_PATH = DATASETS_DIR / "golden_scenarios.jsonl"
EVIDENCE_PATH = DATASETS_DIR / "frozen_evidence.jsonl"


def _load_jsonl(path: Path, model_cls):
    return [
        model_cls.model_validate_json(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--mode", choices=["frozen", "live"], default="frozen")
    parser.add_argument(
        "--repetitions",
        type=int,
        default=1,
        help="60x1=dev, 60x3=release-candidate, 60x5=major-release",
    )
    parser.add_argument(
        "--dataset-version", default=None, help="Informational only; filters nothing yet"
    )
    parser.add_argument(
        "--evidence-version", default=None, help="Informational only; filters nothing yet"
    )
    parser.add_argument(
        "--top-k", type=int, default=None, help="Overrides Settings.retrieval_top_k for this run"
    )
    parser.add_argument(
        "--report-out", default=None, help="Optional path to also write the report to a file"
    )
    args = parser.parse_args(argv)

    if args.mode == "live":
        print(
            "--mode live is not implemented — this runner only supports frozen regression runs.",
            file=sys.stderr,
        )
        return 2

    if not GOLDEN_PATH.exists() or not EVIDENCE_PATH.exists():
        print(
            "Golden Dataset / Frozen Evidence Corpus not found under eval/datasets/.\n"
            "Run `uv run python eval/datasets/generate_golden_dataset.py` first, "
            "then re-run this command.",
            file=sys.stderr,
        )
        return 2

    from langsmith import Client

    from app.config import get_settings
    from eval.langsmith.run_experiment import DATASET_NAME, run_experiment
    from eval.reports.generate_report import generate_report, write_report
    from eval.schemas.eval_models import EvidenceRecord, GoldenScenario

    settings = get_settings()
    if args.top_k is not None:
        settings.retrieval_top_k = args.top_k

    try:
        scenarios = _load_jsonl(GOLDEN_PATH, GoldenScenario)
        evidence = _load_jsonl(EVIDENCE_PATH, EvidenceRecord)
    except Exception as exc:  # noqa: BLE001 — surface a clean message, not a raw traceback
        print(f"Failed to load Golden Dataset / Frozen Evidence Corpus: {exc}", file=sys.stderr)
        return 2

    client = Client()
    if not client.has_dataset(dataset_name=DATASET_NAME):
        print(
            f"LangSmith dataset {DATASET_NAME!r} not found.\n"
            "Run `uv run python -m eval.langsmith.create_golden_dataset` first, "
            "then re-run this command.",
            file=sys.stderr,
        )
        return 2

    report = run_experiment(
        scenarios,
        evidence,
        settings,
        repetitions=args.repetitions,
        client=client,
    )

    text = generate_report(report)
    print(text)
    if args.report_out:
        write_report(report, args.report_out)

    return 1 if report.gate_result.status == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
