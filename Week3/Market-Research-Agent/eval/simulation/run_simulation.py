#!/usr/bin/env python
"""Batch scenario runner: drives eval/simulation/scenarios.py::SCENARIOS
through the real Discovery, Web Research, and Analysis & Verification
agents end-to-end against real providers, persisting through the real audit
tables exactly like a live run would (a real `runs` row, real
`discovery_candidates` rows, real `research_evidence` rows — this is what
lets Future AGI tracing, if enabled, show these as ordinary traced runs).

Structural checks (candidate count, whether the budget gate should have
tripped) are plain Python, mirroring the deterministic checks tests/ already
covers for the compiled graph — this script does not run the LangGraph state
machine itself (no Send-based concurrency, no checkpointer), it calls the
same agents directly the graph nodes call, the same pattern
eval/run_discovery_eval.py and eval/run_analysis_eval.py already use.

See eval/README.md before running. Needs real OPENAI_API_KEY, YOUCOM_API_KEY,
PINECONE_API_KEY, and a reachable DATABASE_URL (optionally SERPER_API_KEY +
SERPER_ENABLED=true, and FI_API_KEY/FI_SECRET_KEY for the Future AGI
relevancy cross-check). Writes real rows to whatever DATABASE_URL points at
— point it at a scratch/dev database, not a database you care about keeping
clean. Never runs by default, never part of `uv run pytest`."""

import argparse
import json

from dotenv import load_dotenv

load_dotenv()

from fi.evals import evaluate  # noqa: E402

from app.agents.analysis_agent import AnalysisVerificationAgent  # noqa: E402
from app.agents.discovery_agent import DiscoveryAgent  # noqa: E402
from app.agents.web_research_agent import WebResearchAgent  # noqa: E402
from app.clients.futureagi_client import init_futureagi_tracing  # noqa: E402
from app.clients.pinecone_client import PineconeClient  # noqa: E402
from app.clients.youcom_client import YouComClient  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.db.session import get_session_factory  # noqa: E402
from app.graphs.research_analysis_graph import build_search_clients  # noqa: E402
from app.schemas.discovery import DiscoveryRequest  # noqa: E402
from app.services import discovery_service, run_service  # noqa: E402
from app.services.cost_service import project_cost  # noqa: E402
from eval.simulation.scenarios import SCENARIOS  # noqa: E402

TOP_N_SELECTED = 3


def run_scenario(scenario: dict, settings, pinecone: PineconeClient) -> dict:
    session_factory = get_session_factory(settings)
    db = session_factory()
    report: dict = {"scenario": scenario["name"]}

    try:
        workspace = run_service.ensure_default_workspace(db)
        request = DiscoveryRequest(**scenario["request"])
        budget_usd_limit = scenario.get("budget_usd_limit", settings.default_budget_usd_limit)
        run = run_service.create_run(db, workspace.id, request, budget_usd_limit)
        report["run_id"] = str(run.id)

        youcom = YouComClient(settings.youcom_api_key, settings.youcom_base_url)
        discovery_agent = DiscoveryAgent(settings, youcom)
        normalized = discovery_agent.normalize_request(request.model_dump())
        queries = discovery_agent.generate_queries(normalized.model_dump())
        raw_results = discovery_agent.search(queries)
        candidates = discovery_agent.score_candidates(normalized.model_dump(), raw_results)
        report["candidate_count"] = len(candidates)

        expect = scenario.get("expect", {})
        min_candidates = expect.get("min_candidates", 1)
        if len(candidates) < min_candidates:
            report["outcome"] = "FAIL: fewer than expected candidates"
            run_service.update_status(db, run.id, "discovery_failed")
            return report

        rows = discovery_service.persist_candidates(db, run.id, candidates)
        run_service.update_status(db, run.id, "awaiting_selection")

        selected = sorted(rows, key=lambda r: r.match_score, reverse=True)[:TOP_N_SELECTED]

        search_clients = build_search_clients(settings)
        projected_cost = project_cost(
            num_competitors=len(selected), search_provider_count=len(search_clients)
        )
        report["projected_cost_usd"] = projected_cost
        report["budget_usd_limit"] = budget_usd_limit
        budget_gate_triggered = projected_cost > budget_usd_limit
        report["budget_gate_triggered"] = budget_gate_triggered

        if expect.get("expect_budget_gate") and not budget_gate_triggered:
            report["outcome"] = "FAIL: expected the budget gate to trip but it didn't"
            return report

        if budget_gate_triggered:
            run_service.update_status(db, run.id, "awaiting_budget_approval")
            report["outcome"] = "PASS (stopped at budget gate, as expected)"
            return report

        run_service.update_status(db, run.id, "research_running")
        web_agent = WebResearchAgent(settings, search_clients, pinecone)
        analysis_agent = AnalysisVerificationAgent(settings, pinecone)

        competitor_reports = []
        for candidate in selected:
            web_result = web_agent.research(
                db=db,
                run_id=run.id,
                workspace_id=str(workspace.id),
                competitor_id=candidate.id,
                competitor_name=candidate.company_name,
                news_window_days=request.news_window_days,
            )
            profile = analysis_agent.analyze(
                workspace_id=str(workspace.id),
                run_id=run.id,
                competitor_id=candidate.id,
                competitor_name=candidate.company_name,
            )
            competitor_report = {
                "competitor_name": candidate.company_name,
                "evidence_count": len(web_result.evidence_ids),
                "web_research_failures": web_result.failures,
                "coverage_score": profile.evidence_coverage_score,
                "overall_confidence": profile.overall_confidence.value,
            }
            competitor_reports.append(competitor_report)

        report["competitors"] = competitor_reports
        run_service.update_status(db, run.id, "complete")

        low_coverage_names = [
            c["competitor_name"] for c in competitor_reports if c["coverage_score"] == 0.0
        ]
        if low_coverage_names and not expect.get("allow_low_coverage"):
            report["outcome"] = f"FAIL: zero coverage for {low_coverage_names}"
        else:
            report["outcome"] = "PASS"

        return report
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scenario", help="Run only the named scenario instead of all of them", default=None
    )
    args = parser.parse_args()

    settings = get_settings()
    init_futureagi_tracing(settings)
    pinecone = PineconeClient(settings)
    pinecone.ensure_index()

    scenarios = SCENARIOS
    if args.scenario:
        scenarios = [s for s in SCENARIOS if s["name"] == args.scenario]
        if not scenarios:
            raise SystemExit(
                f"No scenario named {args.scenario!r}; known: {[s['name'] for s in SCENARIOS]}"
            )

    reports = []
    for scenario in scenarios:
        print(f"\n=== {scenario['name']} ===")
        report = run_scenario(scenario, settings, pinecone)
        reports.append(report)
        print(json.dumps(report, indent=2, default=str))

        for competitor in report.get("competitors", []):
            summary = (
                f"{competitor['competitor_name']}: coverage="
                f"{competitor['coverage_score']:.2f}, confidence={competitor['overall_confidence']}"
            )
            fi_result = evaluate(
                "answer_relevancy",
                input=f"Competitive research summary for {competitor['competitor_name']}",
                output=summary,
            )
            print(f"  Future AGI relevancy check: {fi_result.score:.2f} — {fi_result.reason}")

    passed = sum(1 for r in reports if str(r.get("outcome", "")).startswith("PASS"))
    print(f"\n{passed}/{len(reports)} scenarios passed.")


if __name__ == "__main__":
    main()
