import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from eval.datasets.generate_golden_dataset import EVIDENCE_PATH, SCENARIOS_PATH
from eval.schemas.eval_models import EvidenceRecord, GoldenScenario

EXPECTED_CASE_TYPE_DISTRIBUTION = {
    "PASS": 15,
    "RETRIEVAL": 10,
    "RED_FLAG": 8,
    "MISSING_INFO": 7,
    "CONFLICT": 8,
    "COVERAGE_FRESHNESS": 5,
    "COST": 2,
    "TEMPORAL": 3,
    "RESILIENCE": 2,
}


def _read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


@pytest.fixture(scope="module")
def scenario_rows() -> list[dict]:
    return _read_jsonl(SCENARIOS_PATH)


@pytest.fixture(scope="module")
def evidence_rows() -> list[dict]:
    return _read_jsonl(EVIDENCE_PATH)


@pytest.fixture(scope="module")
def scenarios(scenario_rows: list[dict]) -> list[GoldenScenario]:
    return [GoldenScenario.model_validate(row) for row in scenario_rows]


@pytest.fixture(scope="module")
def evidence_records(evidence_rows: list[dict]) -> list[EvidenceRecord]:
    return [EvidenceRecord.model_validate(row) for row in evidence_rows]


def test_files_exist():
    assert EVIDENCE_PATH.exists()
    assert SCENARIOS_PATH.exists()


def test_every_scenario_validates_against_golden_scenario(scenario_rows: list[dict]):
    for row in scenario_rows:
        GoldenScenario.model_validate(row)


def test_every_evidence_record_validates_and_hash_matches(evidence_rows: list[dict]):
    for row in evidence_rows:
        record = EvidenceRecord.model_validate(row)
        expected_hash = hashlib.sha256(record.content.encode("utf-8")).hexdigest()
        assert record.content_sha256 == expected_hash, (
            f"content_sha256 mismatch for {record.evidence_id}"
        )


def test_every_referenced_evidence_id_exists_in_corpus(
    scenarios: list[GoldenScenario], evidence_records: list[EvidenceRecord]
):
    known_ids = {e.evidence_id for e in evidence_records}
    for scenario in scenarios:
        ref = scenario.reference_outputs
        referenced: set[str] = set()
        referenced.update(ref.relevant_evidence_ids)
        referenced.update(ref.required_evidence_ids)
        for rf in ref.expected_red_flags:
            referenced.update(rf.expected_evidence_ids)
        for c in ref.expected_conflicts:
            referenced.update(c.evidence_ids_a)
            referenced.update(c.evidence_ids_b)
        for f in ref.gold_facts:
            referenced.update(f.evidence_ids)

        missing = referenced - known_ids
        assert not missing, (
            f"{scenario.inputs.scenario_id} references missing evidence_ids: {missing}"
        )


def test_exactly_60_scenarios_with_expected_case_type_distribution(scenarios: list[GoldenScenario]):
    assert len(scenarios) == 60

    counts: dict[str, int] = {}
    for scenario in scenarios:
        counts[scenario.metadata.case_type] = counts.get(scenario.metadata.case_type, 0) + 1

    assert counts == EXPECTED_CASE_TYPE_DISTRIBUTION


def test_scenario_ids_are_unique_and_exactly_mr_001_through_mr_060(scenarios: list[GoldenScenario]):
    scenario_ids = [s.inputs.scenario_id for s in scenarios]
    assert len(scenario_ids) == len(set(scenario_ids)), "duplicate scenario_id found"

    expected_ids = {f"MR-{i:03d}" for i in range(1, 61)}
    assert set(scenario_ids) == expected_ids


def test_all_gold_versions_are_gold_v1(scenarios: list[GoldenScenario]):
    for scenario in scenarios:
        assert scenario.metadata.gold_version == "gold-v1"


def test_invalid_evidence_record_is_rejected():
    with pytest.raises(ValidationError):
        EvidenceRecord.model_validate(
            {
                "evidence_id": "EV-999999",
                "company": "X",
                "category": "pricing",
                "source_type": "not_a_real_source_type",
                "url": "https://example.com",
                "title": "X",
                "retrieved_at": "2026-01-01T00:00:00Z",
                "content": "content",
                "chunk_id": "EV-999999-chunk-0",
                "content_sha256": hashlib.sha256(b"content").hexdigest(),
            }
        )
