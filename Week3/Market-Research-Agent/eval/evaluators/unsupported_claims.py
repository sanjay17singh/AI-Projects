"""Unsupported-claim / hallucination rate. Whether an individual material
claim is actually supported by its cited evidence is an LLM-as-judge call
(judges/faithfulness_judge.py, whose `unsupported_items` list feeds the
numerator here) — this module is pure arithmetic over the judge's tally so
the rate calculation itself stays deterministic and unit-testable."""


def unsupported_claim_rate(total_material_claims: int, unsupported_material_claims: int) -> float:
    """Unsupported material claims / total material claims. Zero material
    claims -> 0.0 (nothing to be unsupported), not a divide-by-zero."""
    if total_material_claims <= 0:
        return 0.0
    return round(unsupported_material_claims / total_material_claims, 4)
