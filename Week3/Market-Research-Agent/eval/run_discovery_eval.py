#!/usr/bin/env python
"""Runs the Discovery Agent quality eval against real OpenAI (and, with
--live, real You.com). See eval/README.md before running this."""

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

# Must happen before `from langsmith import Client` is used below — the
# langsmith SDK reads LANGCHAIN_API_KEY/LANGSMITH_API_KEY straight from
# os.environ, not from app.config.Settings, and nothing else in this
# process loads .env into the real environment.
load_dotenv()

from langsmith import Client, evaluate  # noqa: E402

from app.agents.discovery_agent import DiscoveryAgent  # noqa: E402
from app.clients.youcom_client import YouComClient  # noqa: E402
from app.config import get_settings  # noqa: E402
from eval.evaluators.discovery_evaluators import DISCOVERY_EVALUATORS  # noqa: E402

DATASET_NAME = "market-research-agent-discovery-examples"
DATASET_PATH = Path(__file__).parent / "datasets" / "discovery_examples.json"

# Used when --live is not passed, so this eval stays fast/cheap by default —
# a fixed set of plausible search results rather than a real You.com call.
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
        from app.schemas.research import RawSearchResult

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


def ensure_dataset(client: Client) -> None:
    if client.has_dataset(dataset_name=DATASET_NAME):
        return
    client.create_dataset(dataset_name=DATASET_NAME, description="Discovery Agent eval examples")
    examples = json.loads(DATASET_PATH.read_text())
    client.create_examples(dataset_name=DATASET_NAME, examples=examples)


def make_target(live: bool):
    settings = get_settings()
    youcom = (
        YouComClient(settings.youcom_api_key, settings.youcom_base_url) if live else FixtureYouCom()
    )
    agent = DiscoveryAgent(settings, youcom)

    def target(inputs: dict) -> dict:
        normalized = agent.normalize_request(inputs)
        queries = agent.generate_queries(normalized.model_dump())
        raw_results = agent.search(queries)
        candidates = agent.score_candidates(normalized.model_dump(), raw_results)
        return {"candidates": [c.model_dump(mode="json") for c in candidates]}

    return target


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--live", action="store_true", help="Use the real You.com API instead of fixtures"
    )
    args = parser.parse_args()

    client = Client()
    ensure_dataset(client)

    results = evaluate(
        make_target(args.live),
        data=DATASET_NAME,
        evaluators=DISCOVERY_EVALUATORS,
        experiment_prefix="discovery-agent",
        client=client,
    )
    print(results)


if __name__ == "__main__":
    main()
