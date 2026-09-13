from eval.evaluators.coverage import ground_truth_coverage, ground_truth_coverage_by_category
from eval.evaluators.red_flag_precision import red_flag_precision
from eval.evaluators.red_flag_recall import critical_red_flag_recall, red_flag_recall
from eval.evaluators.retrieval_precision import precision_at_k
from eval.evaluators.retrieval_recall import recall_at_k
from eval.schemas.eval_models import GoldFact, GoldRedFlag


def test_precision_at_5_example_from_spec():
    retrieved = ["EV001", "EV002", "EV003", "EV004", "EV005"]
    relevant = {"EV001", "EV002", "EV004"}
    assert precision_at_k(retrieved, relevant, 5) == 0.60


def test_precision_at_k_empty_retrieval_is_zero():
    assert precision_at_k([], {"EV001"}, 5) == 0.0


def test_precision_at_k_k_larger_than_retrieved_set_divides_by_k_not_len():
    # Only 2 retrieved out of a requested 5 -> penalized, not inflated.
    assert precision_at_k(["EV001", "EV002"], {"EV001", "EV002"}, 5) == 0.40


def test_recall_at_k_no_expected_relevant_is_vacuous_one():
    assert recall_at_k(["EV001"], set(), 5) == 1.0


def test_recall_at_k_k_larger_than_retrieved_set():
    assert recall_at_k(["EV001"], {"EV001", "EV002"}, 5) == 0.5


def test_red_flag_recall_no_expected_flags_is_vacuous_one():
    assert red_flag_recall([], set()) == 1.0


def test_critical_red_flag_recall_must_be_full_when_any_critical_missed():
    gold = [
        GoldRedFlag(
            red_flag_id="RF-1",
            type="security_incident",
            description="breach",
            severity="critical",
            is_critical=True,
            expected_agent_response="flag it",
        ),
        GoldRedFlag(
            red_flag_id="RF-2",
            type="price_increase",
            description="up 20%",
            severity="medium",
            is_critical=False,
            expected_agent_response="flag it",
        ),
    ]
    # Only the non-critical one matched.
    assert critical_red_flag_recall(gold, {"RF-2"}) == 0.0
    assert red_flag_recall(gold, {"RF-2"}) == 0.5
    assert critical_red_flag_recall(gold, {"RF-1", "RF-2"}) == 1.0


def test_red_flag_precision_no_agent_flags_is_vacuous_one():
    assert red_flag_precision([], set()) == 1.0


def test_ground_truth_coverage_no_gold_facts_is_vacuous_one():
    assert ground_truth_coverage([], set()) == 1.0


def test_ground_truth_coverage_by_category():
    facts = [
        GoldFact(fact_id="F1", category="pricing", statement="..."),
        GoldFact(fact_id="F2", category="pricing", statement="..."),
        GoldFact(fact_id="F3", category="features", statement="..."),
    ]
    result = ground_truth_coverage_by_category(facts, {"F1", "F3"})
    assert result == {"pricing": 0.5, "features": 1.0}
