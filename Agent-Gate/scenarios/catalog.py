"""Loads and validates every scenario YAML file into ScenarioDefinition objects.

This is the mandatory scenario catalog referenced by the Scenario Design Agent
and used as the fallback source of truth when Pinecone is unavailable.
"""

from functools import lru_cache
from pathlib import Path

import yaml

from scenarios.schema import ScenarioDefinition

CATALOG_ROOT = Path(__file__).parent
BUCKET_DIRS = ("adversarial", "benign", "resilience")


class CatalogValidationError(Exception):
    pass


def _load_dir(bucket: str) -> list[ScenarioDefinition]:
    directory = CATALOG_ROOT / bucket
    scenarios = []
    for path in sorted(directory.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text())
        try:
            scenario = ScenarioDefinition.model_validate(raw)
        except Exception as exc:
            raise CatalogValidationError(f"{path}: {exc}") from exc
        if scenario.bucket != bucket:
            raise CatalogValidationError(
                f"{path}: bucket field '{scenario.bucket}' does not match directory '{bucket}'"
            )
        scenarios.append(scenario)
    return scenarios


@lru_cache
def load_catalog() -> tuple[ScenarioDefinition, ...]:
    all_scenarios: list[ScenarioDefinition] = []
    for bucket in BUCKET_DIRS:
        all_scenarios.extend(_load_dir(bucket))

    ids = [s.id for s in all_scenarios]
    duplicates = {i for i in ids if ids.count(i) > 1}
    if duplicates:
        raise CatalogValidationError(f"duplicate scenario IDs: {duplicates}")

    return tuple(all_scenarios)


def get_scenario(scenario_id: str) -> ScenarioDefinition:
    for scenario in load_catalog():
        if scenario.id == scenario_id:
            return scenario
    raise KeyError(f"unknown scenario id: {scenario_id}")


def by_category(category: str) -> list[ScenarioDefinition]:
    return [s for s in load_catalog() if s.category == category]


def by_bucket(bucket: str) -> list[ScenarioDefinition]:
    return [s for s in load_catalog() if s.bucket == bucket]
