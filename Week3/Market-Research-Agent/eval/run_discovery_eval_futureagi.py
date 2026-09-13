#!/usr/bin/env python
"""Second, independent quality check for the Discovery Agent, using Future
AGI's evaluate() instead of LangSmith's evaluate(). Runs alongside
eval/run_discovery_eval.py by explicit product decision — not a replacement
for it — so a regression that one judge misses has a chance of being caught
by the other.

Requires the optional `futureagi` uv dependency group
(`uv sync --group futureagi`) plus FI_API_KEY/FI_SECRET_KEY. See
eval/README.md before running — same credential tier as the rest of eval/:
never runs by default, never part of `uv run pytest`.

Metric identifier note: "answer_relevancy" is used below because it's one of
the few metric names Future AGI's own published code samples show verbatim
(alongside "faithfulness", "toxicity", "contains"). Their built-in-evals
overview page also describes "Context Relevance" as a distinct metric more
semantically suited to scoring a competitor list's relevance to a request,
but its exact callable identifier string wasn't confirmed in a code sample —
rather than guess it (the same category of mistake that produced a real bug
in app/clients/youcom_client.py earlier in this project), this script sticks
to confirmed identifiers only. Swap in "context_relevance" once its exact
slug is confirmed against the installed ai-evaluation package."""

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

# Must happen before Future AGI / LangChain imports below — see the matching
# comment in run_discovery_eval.py for why.
load_dotenv()

from fi.evals import evaluate  # noqa: E402

from app.agents.discovery_agent import DiscoveryAgent  # noqa: E402
from app.clients.futureagi_client import init_futureagi_tracing  # noqa: E402
from app.clients.youcom_client import YouComClient  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.schemas.research import RawSearchResult  # noqa: E402

DATASET_PATH = Path(__file__).parent / "datasets" / "discovery_examples.json"

# Same fixture used by run_discovery_eval.py's default (non --live) path.
FIXTURE_SEARCH_RESULTS = [
    {
        "title": "Example result",
        "url": "https://example.com",
        "snippet": "A relevant result.",
        "highlights": None,
    }
]


class FixtureYouCom:
    def search_web(self, query, category, count=10):
        return [
            RawSearchResult(
                title=r["title"],
                url=r["url"],
                snippet=r["snippet"],
                highlights=r["highlights"],
                published_at=None,
                category=category,
                query_used=query,
                source_type="web",
            )
            for r in FIXTURE_SEARCH_RESULTS
        ]


def run_row(agent: DiscoveryAgent, inputs: dict) -> list[dict]:
    normalized = agent.normalize_request(inputs)
    queries = agent.generate_queries(normalized.model_dump())
    raw_results = agent.search(queries)
    candidates = agent.score_candidates(normalized.model_dump(), raw_results)
    return [c.model_dump(mode="json") for c in candidates]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--live", action="store_true", help="Use the real You.com API instead of fixtures"
    )
    args = parser.parse_args()

    settings = get_settings()
    init_futureagi_tracing(settings)  # so this run also shows up as a trace, if enabled

    youcom = (
        YouComClient(settings.youcom_api_key, settings.youcom_base_url)
        if args.live
        else FixtureYouCom()
    )
    agent = DiscoveryAgent(settings, youcom)

    examples = json.loads(DATASET_PATH.read_text())
    scores = []
    for example in examples:
        inputs = example["inputs"]
        candidates = run_row(agent, inputs)

        candidates_block = "\n".join(
            f"- {c['company_name']} ({c['classification']}): {c['explanation']}" for c in candidates
        )
        request_block = (
            f"Target company: {inputs['target_company_name']}\n"
            f"Industry: {inputs.get('industry')}\n"
            f"Geography: {inputs.get('geography')}\n"
            f"Customer segment: {inputs.get('customer_segment')}"
        )

        result = evaluate("answer_relevancy", input=request_block, output=candidates_block)
        scores.append(result.score)
        print(
            f"{inputs['target_company_name']}: "
            f"candidates={len(candidates)} relevancy={result.score:.2f} — {result.reason}"
        )

    if scores:
        print(f"\nAverage relevancy across {len(scores)} examples: {sum(scores) / len(scores):.2f}")


if __name__ == "__main__":
    main()
