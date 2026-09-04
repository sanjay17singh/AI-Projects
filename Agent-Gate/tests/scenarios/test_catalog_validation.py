"""Validates the mandatory 40-scenario catalog: counts, categories, uniqueness, schema."""

from collections import Counter

from scenarios.catalog import load_catalog

ADVERSARIAL_CATEGORIES = {
    "adversarial_direct_injection": 4,
    "adversarial_indirect_injection": 4,
    "adversarial_cross_customer": 4,
    "adversarial_unauthorized_refund": 4,
}
BENIGN_CATEGORIES = {
    "benign_lookup": 2,
    "benign_low_value_refund": 2,
    "benign_escalation_refund": 2,
    "benign_kb_question": 2,
    "benign_data_correction": 2,
    "benign_ticket_creation": 2,
    "benign_unavailable_info": 2,
    "benign_safe_refusal": 2,
}
RESILIENCE_CATEGORIES = {
    "resilience_budget_approval": 1,
    "resilience_guardrail_approval": 1,
    "resilience_guardrail_rejection": 1,
    "resilience_checkpoint_recovery": 1,
    "resilience_duplicate_decision": 1,
    "resilience_pinecone_outage": 1,
    "resilience_postgres_failure": 1,
    "resilience_openai_failure": 1,
}


def test_total_scenario_count_is_40():
    assert len(load_catalog()) == 40


def test_bucket_distribution():
    counts = Counter(s.bucket for s in load_catalog())
    assert counts == {"adversarial": 16, "benign": 16, "resilience": 8}


def test_adversarial_category_distribution():
    counts = Counter(s.category for s in load_catalog() if s.bucket == "adversarial")
    assert counts == ADVERSARIAL_CATEGORIES


def test_benign_category_distribution():
    counts = Counter(s.category for s in load_catalog() if s.bucket == "benign")
    assert counts == BENIGN_CATEGORIES


def test_resilience_category_distribution():
    counts = Counter(s.category for s in load_catalog() if s.bucket == "resilience")
    assert counts == RESILIENCE_CATEGORIES


def test_all_scenario_ids_unique():
    ids = [s.id for s in load_catalog()]
    assert len(ids) == len(set(ids))


def test_every_scenario_has_at_least_one_deterministic_assertion():
    for s in load_catalog():
        assert len(s.deterministic_assertions) >= 1, s.id


def test_every_scenario_has_required_narrative_fields():
    for s in load_catalog():
        assert s.description.strip()
        assert s.expected_behavior.strip()
        assert s.forbidden_behavior.strip()
        assert s.input_messages, s.id


def test_every_scenario_has_tags():
    for s in load_catalog():
        assert s.tags, s.id
