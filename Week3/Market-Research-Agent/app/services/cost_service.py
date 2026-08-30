"""Cost projection and the spend ledger. PRICE_TABLE is the one place to edit
when provider pricing changes — deliberately a plain constant rather than a
dozen extra env vars, since these numbers are looked up, not tuned per-deploy.
Everything here is plain arithmetic; no LLM calls."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import Run, RunCost

# USD per unit. Placeholder ballpark figures for gpt-4o-mini-class pricing —
# update to match whatever OPENAI_MODEL/OPENAI_MODEL_FAST actually cost.
PRICE_TABLE: dict[str, dict[str, float]] = {
    "you_com": {"api_call": 0.010},
    "serper": {"api_call": 0.010},  # placeholder — update to Serper's real per-call rate
    "openai": {
        "tokens_in": 0.00000015,
        "tokens_out": 0.00000060,
        "embedding_tokens": 0.00000002,
    },
    "pinecone": {"api_call": 0.0004},
}

# Rough per-call token estimates used only for the pre-flight projection —
# actual spend is tracked separately via record_cost() as calls happen.
AVG_EXTRACTION_TOKENS_IN = 3500
AVG_EXTRACTION_TOKENS_OUT = 900
CATEGORIES_PER_COMPETITOR = 11  # 10 research categories + news


def project_cost(num_competitors: int, search_provider_count: int = 1) -> float:
    """search_provider_count reflects how many search clients are actually
    configured (You.com alone = 1; + Serper = 2) — every configured provider
    is called once per category, so the search-cost portion scales linearly
    with it."""
    search_cost = (
        CATEGORIES_PER_COMPETITOR * PRICE_TABLE["you_com"]["api_call"] * search_provider_count
    )
    extraction_cost = (
        AVG_EXTRACTION_TOKENS_IN * PRICE_TABLE["openai"]["tokens_in"]
        + AVG_EXTRACTION_TOKENS_OUT * PRICE_TABLE["openai"]["tokens_out"]
    )
    retrieval_embedding_cost = (
        CATEGORIES_PER_COMPETITOR * 50 * PRICE_TABLE["openai"]["embedding_tokens"]
    )
    per_competitor = search_cost + extraction_cost + retrieval_embedding_cost
    return round(per_competitor * num_competitors, 4)


def record_cost(
    db: Session,
    run_id: UUID,
    node_name: str,
    provider: str,
    unit_type: str,
    quantity: float,
    unit_cost_usd: float | None = None,
) -> float:
    unit_cost = (
        unit_cost_usd
        if unit_cost_usd is not None
        else PRICE_TABLE.get(provider, {}).get(unit_type, 0.0)
    )
    cost_usd = round(quantity * unit_cost, 4)

    db.add(
        RunCost(
            run_id=run_id,
            node_name=node_name,
            provider=provider,
            unit_type=unit_type,
            quantity=quantity,
            unit_cost_usd=unit_cost,
            cost_usd=cost_usd,
        )
    )
    run = db.get(Run, run_id)
    if run is not None:
        run.actual_cost_usd = float(run.actual_cost_usd or 0) + cost_usd
    db.commit()
    return cost_usd
