"""Synthetic edge-case research requests for run_simulation.py.

Future AGI's own simulate-sdk (TestRunner/Persona/Scenario) is built for
multi-turn conversational or voice agents — pointing it at this app directly
would mean force-fitting a chat-persona model onto a bounded, single-shot
research pipeline it wasn't designed for. Rather than guess at an
`agent_callback` contract that isn't precisely documented for a non-chat
agent (the same category of risk flagged in app/clients/futureagi_client.py
and run_discovery_eval_futureagi.py), "simulation" here means something more
modest but still genuinely useful: batch-driving these scenarios through the
real pipeline end-to-end and scoring the results — structurally, and via
Future AGI's evaluate() where a real credential-tier judgment is useful.

Each scenario is a plain DiscoveryRequest-shaped dict plus optional
`budget_usd_limit` override and `expect` assertions checked by
run_simulation.py."""

SCENARIOS = [
    {
        "name": "ambiguous_industry",
        "request": {
            "target_company_name": "Aria",
            "industry": "software",  # deliberately vague, one word
            "geography": "Global",
            "customer_segment": None,
            "news_window_days": 60,
        },
        "expect": {"min_candidates": 5},
    },
    {
        "name": "near_zero_public_info",
        "request": {
            "target_company_name": "Quietstack Analytics",  # obscure, likely sparse coverage
            "industry": "Data infrastructure",
            "geography": "United States",
            "customer_segment": "Enterprise",
            "news_window_days": 90,
        },
        "expect": {"min_candidates": 5, "allow_low_coverage": True},
    },
    {
        "name": "non_english_company_name",
        "request": {
            "target_company_name": "株式会社メルカリ",  # Mercari
            "industry": "E-commerce marketplace",
            "geography": "Japan",
            "customer_segment": "Consumers",
            "news_window_days": 60,
        },
        "expect": {"min_candidates": 5},
    },
    {
        "name": "budget_gate_trigger",
        "request": {
            "target_company_name": "Salesforce",
            "industry": "CRM software",
            "geography": "Global",
            "customer_segment": "Enterprise",
            "news_window_days": 365,  # widest window → highest projected cost
        },
        "budget_usd_limit": 0.05,  # deliberately far below any plausible projection
        "expect": {"min_candidates": 5, "expect_budget_gate": True},
    },
]
