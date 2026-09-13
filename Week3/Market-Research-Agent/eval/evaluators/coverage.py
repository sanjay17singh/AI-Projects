"""Ground Truth Coverage — NOT the same thing as the agent's own
`evidence_coverage_score` (app/services/analysis_service.compute_coverage_score,
which only checks "is this category non-empty"). This measures how many of
the Golden Dataset's individually-listed `gold_facts` were actually recovered
by the agent, which requires semantic matching (judges/coverage_judge.py) —
this module just turns a recovered-fact-id set into ratios."""

from collections import defaultdict

from eval.schemas.eval_models import GoldFact


def ground_truth_coverage(gold_facts: list[GoldFact], recovered_fact_ids: set[str]) -> float:
    """Recovered Golden Facts / Total Golden Facts. No gold facts defined for
    a scenario -> vacuous 1.0."""
    if not gold_facts:
        return 1.0
    recovered = {f.fact_id for f in gold_facts} & recovered_fact_ids
    return round(len(recovered) / len(gold_facts), 4)


def ground_truth_coverage_by_category(
    gold_facts: list[GoldFact], recovered_fact_ids: set[str]
) -> dict[str, float]:
    by_category: dict[str, list[GoldFact]] = defaultdict(list)
    for fact in gold_facts:
        by_category[fact.category].append(fact)
    return {
        category: ground_truth_coverage(facts, recovered_fact_ids)
        for category, facts in by_category.items()
    }
