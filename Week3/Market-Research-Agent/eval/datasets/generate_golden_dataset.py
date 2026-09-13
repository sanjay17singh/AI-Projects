"""Deterministic generator for the 60-scenario Golden Dataset and its matching
Frozen Evidence Corpus.

Run with:
    uv run python -m eval.datasets.generate_golden_dataset

Produces (overwriting):
    eval/datasets/frozen_evidence.jsonl
    eval/datasets/golden_scenarios.jsonl

Every evidence_id referenced anywhere in a GoldenScenario (relevant/required
evidence ids, gold red-flag/conflict/fact evidence ids) must exist in the
frozen corpus this script writes — that invariant is asserted at the end of
`main()` and re-checked in eval/tests/test_generate_golden_dataset.py.

No network calls, no app/ runtime imports, no randomness — evidence_ids are
assigned in a monotonically increasing, zero-padded sequence ("EV-000001",
...) in the order records are created, so re-running this script produces
byte-identical output.
"""

# ruff: noqa: E501 — evidence `content` strings are realistic-length scraped
# snippets by design; wrapping them would hurt readability for no benefit
# since this is a one-time data-generation script, not runtime code.

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from eval.schemas.eval_models import (
    CostRange,
    EvidenceRecord,
    GoldConflict,
    GoldenScenario,
    GoldFact,
    GoldRedFlag,
    ScenarioInputs,
    ScenarioMetadata,
    ScenarioReferenceOutputs,
)

DATASETS_DIR = Path(__file__).parent
EVIDENCE_PATH = DATASETS_DIR / "frozen_evidence.jsonl"
SCENARIOS_PATH = DATASETS_DIR / "golden_scenarios.jsonl"

RETRIEVED_AT = "2026-06-01T00:00:00Z"
GOLD_VERSION = "gold-v1"

# Reused fictional company pool -- keeps the corpus feeling coherent instead
# of 60 disposable one-off names. None of these correspond to real companies.
PIPELINE_HARBOR = "Pipeline Harbor"
NORTHWIND = "Northwind Analytics"
VANTAGE_LOOP = "Vantage Loop"
COBALT_MERIDIAN = "Cobalt Meridian"
FERNBRIDGE = "Fernbridge Data"
SOLACE_METRICS = "Solace Metrics"
ANCHORPOINT = "Anchorpoint AI"
LUMEN_CASCADE = "Lumen Cascade"
DRIFTWOOD = "Driftwood Systems"
HARBORLIGHT = "Harborlight Cloud"


class Builder:
    def __init__(self) -> None:
        self._evidence_counter = 0
        self.evidence: list[EvidenceRecord] = []
        self.scenarios: list[GoldenScenario] = []

    def ev(
        self,
        company: str,
        category: str,
        source_type: str,
        url: str,
        title: str,
        content: str,
        published_at: str | None = None,
    ) -> str:
        self._evidence_counter += 1
        evidence_id = f"EV-{self._evidence_counter:06d}"
        content_sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
        record = EvidenceRecord(
            evidence_id=evidence_id,
            company=company,
            category=category,
            source_type=source_type,
            url=url,
            title=title,
            published_at=published_at,
            retrieved_at=RETRIEVED_AT,
            content=content,
            chunk_id=f"{evidence_id}-chunk-0",
            content_sha256=content_sha256,
        )
        self.evidence.append(record)
        return evidence_id

    def scenario(
        self,
        scenario_id: str,
        target_company: str,
        competitors: list[str],
        question: str,
        research_category: str,
        case_type: str,
        primary_metric: str,
        difficulty: str = "medium",
        top_k: int = 5,
        simulation: dict | None = None,
        expected_claims: list[str] | None = None,
        expected_red_flags: list[GoldRedFlag] | None = None,
        relevant_evidence_ids: list[str] | None = None,
        required_evidence_ids: list[str] | None = None,
        expected_conflicts: list[GoldConflict] | None = None,
        expected_unknowns: list[str] | None = None,
        gold_facts: list[GoldFact] | None = None,
        expected_current_values: dict[str, str] | None = None,
        expected_cost_range: CostRange | None = None,
    ) -> None:
        scenario = GoldenScenario(
            inputs=ScenarioInputs(
                scenario_id=scenario_id,
                target_company=target_company,
                competitors=competitors,
                question=question,
                research_category=research_category,
                top_k=top_k,
                simulation=simulation or {},
            ),
            reference_outputs=ScenarioReferenceOutputs(
                expected_claims=expected_claims or [],
                expected_red_flags=expected_red_flags or [],
                relevant_evidence_ids=relevant_evidence_ids or [],
                required_evidence_ids=required_evidence_ids or [],
                expected_conflicts=expected_conflicts or [],
                expected_unknowns=expected_unknowns or [],
                gold_facts=gold_facts or [],
                expected_current_values=expected_current_values or {},
                expected_cost_range=expected_cost_range,
            ),
            metadata=ScenarioMetadata(
                case_type=case_type,
                difficulty=difficulty,
                primary_metric=primary_metric,
                gold_version=GOLD_VERSION,
            ),
        )
        self.scenarios.append(scenario)


def build() -> Builder:
    b = Builder()

    # ----------------------------------------------------------------
    # MR-001..015 -- PASS (15): clean, unambiguous scenarios.
    # ----------------------------------------------------------------

    # MR-001: clear pricing
    e1 = b.ev(
        NORTHWIND, "pricing", "official",
        "https://northwindanalytics.io/pricing",
        "Northwind Analytics -- Pricing",
        "Northwind Analytics offers a single self-serve plan priced at $79 per seat per month, "
        "billed monthly with no long-term contract. The price includes all core dashboard "
        "features and up to five data connectors. Enterprise volume discounts are handled "
        "through the sales team and are not listed publicly.",
        published_at="2026-04-02",
    )
    b.scenario(
        "MR-001", PIPELINE_HARBOR, [NORTHWIND],
        "What does Northwind Analytics charge for its product?",
        "pricing", "PASS", "faithfulness", difficulty="easy",
        expected_claims=["Northwind Analytics charges $79 per seat per month, billed monthly."],
        relevant_evidence_ids=[e1], required_evidence_ids=[e1],
        gold_facts=[GoldFact(fact_id="MR-001-F1", category="pricing",
                              statement="Northwind Analytics charges $79/seat/month.",
                              evidence_ids=[e1])],
    )

    # MR-002: multiple pricing tiers
    e2 = b.ev(
        VANTAGE_LOOP, "pricing", "official",
        "https://vantageloop.com/plans",
        "Vantage Loop -- Plans & Pricing",
        "Vantage Loop publishes three tiers: Starter at $29/month for up to 3 users, Growth at "
        "$99/month for up to 20 users with API access, and Scale at $249/month for unlimited "
        "users with SSO and dedicated support. All tiers include a shared core reporting engine, "
        "and higher tiers unlock more granular permissioning.",
        published_at="2026-03-15",
    )
    b.scenario(
        "MR-002", PIPELINE_HARBOR, [VANTAGE_LOOP],
        "What pricing tiers does Vantage Loop offer?",
        "pricing", "PASS", "faithfulness", difficulty="easy",
        expected_claims=["Vantage Loop has three tiers: Starter $29/mo, Growth $99/mo, Scale $249/mo."],
        relevant_evidence_ids=[e2], required_evidence_ids=[e2],
        gold_facts=[GoldFact(fact_id="MR-002-F1", category="pricing",
                              statement="Vantage Loop offers Starter ($29/mo), Growth ($99/mo), and Scale ($249/mo) tiers.",
                              evidence_ids=[e2])],
    )

    # MR-003: monthly vs annual pricing (both stated, not conflicting -- just two figures)
    e3 = b.ev(
        COBALT_MERIDIAN, "pricing", "official",
        "https://cobaltmeridian.com/pricing",
        "Cobalt Meridian -- Pricing",
        "Cobalt Meridian's standard plan is $120 per month, or $1,080 per year when billed "
        "annually -- a 25% discount versus paying monthly. Both billing options include the "
        "same feature set; only the payment cadence differs. The annual plan requires a card "
        "on file and auto-renews.",
        published_at="2026-02-20",
    )
    b.scenario(
        "MR-003", PIPELINE_HARBOR, [COBALT_MERIDIAN],
        "How does Cobalt Meridian's monthly pricing compare to its annual pricing?",
        "pricing", "PASS", "faithfulness", difficulty="easy",
        expected_claims=["Cobalt Meridian charges $120/month or $1,080/year (a 25% annual discount)."],
        relevant_evidence_ids=[e3], required_evidence_ids=[e3],
        gold_facts=[GoldFact(fact_id="MR-003-F1", category="pricing",
                              statement="Cobalt Meridian: $120/month, or $1,080/year (25% discount).",
                              evidence_ids=[e3])],
    )

    # MR-004: explicit product capability
    e4 = b.ev(
        FERNBRIDGE, "core_features", "documentation",
        "https://docs.fernbridgedata.com/features/real-time-sync",
        "Fernbridge Data Documentation -- Real-Time Sync",
        "Fernbridge Data supports real-time bidirectional sync with Salesforce, HubSpot, and "
        "Snowflake, with changes propagating in under 60 seconds under normal load. The sync "
        "engine handles field-level conflict detection and exposes a webhook for downstream "
        "automation when a sync completes.",
        published_at="2026-01-10",
    )
    b.scenario(
        "MR-004", PIPELINE_HARBOR, [FERNBRIDGE],
        "Does Fernbridge Data support real-time data sync with CRMs?",
        "core_features", "PASS", "faithfulness", difficulty="easy",
        expected_claims=["Fernbridge Data supports real-time bidirectional sync with Salesforce, HubSpot, and Snowflake."],
        relevant_evidence_ids=[e4], required_evidence_ids=[e4],
        gold_facts=[GoldFact(fact_id="MR-004-F1", category="core_features",
                              statement="Fernbridge Data offers real-time bidirectional CRM sync (<60s propagation).",
                              evidence_ids=[e4])],
    )

    # MR-005: target customer segment
    e5 = b.ev(
        SOLACE_METRICS, "target_customers", "official",
        "https://solacemetrics.com/customers",
        "Solace Metrics -- Who We Serve",
        "Solace Metrics is built for mid-market B2B SaaS companies with 50-500 employees that "
        "need self-serve analytics without a dedicated data team. The product deliberately "
        "avoids enterprise-only features like on-prem deployment, focusing instead on fast "
        "setup for lean revenue operations teams.",
        published_at="2026-03-01",
    )
    b.scenario(
        "MR-005", PIPELINE_HARBOR, [SOLACE_METRICS],
        "Who is Solace Metrics' target customer segment?",
        "target_customers", "PASS", "faithfulness", difficulty="easy",
        expected_claims=["Solace Metrics targets mid-market B2B SaaS companies (50-500 employees) without a dedicated data team."],
        relevant_evidence_ids=[e5], required_evidence_ids=[e5],
        gold_facts=[GoldFact(fact_id="MR-005-F1", category="target_customers",
                              statement="Solace Metrics targets mid-market B2B SaaS companies (50-500 employees).",
                              evidence_ids=[e5])],
    )

    # MR-006: product positioning
    e6 = b.ev(
        ANCHORPOINT, "positioning", "official",
        "https://anchorpoint.ai/about",
        "Anchorpoint AI -- Our Approach",
        "Anchorpoint AI positions itself as the 'accuracy-first' alternative to faster but "
        "less-precise competitors, explicitly trading response latency for verified, "
        "citation-backed answers. Its marketing repeatedly contrasts this against unnamed "
        "rivals it describes as optimizing for speed over correctness.",
        published_at="2026-04-18",
    )
    b.scenario(
        "MR-006", PIPELINE_HARBOR, [ANCHORPOINT],
        "How does Anchorpoint AI position itself in the market?",
        "positioning", "PASS", "faithfulness", difficulty="easy",
        expected_claims=["Anchorpoint AI positions itself as the accuracy-first alternative, trading speed for verified answers."],
        relevant_evidence_ids=[e6], required_evidence_ids=[e6],
        gold_facts=[GoldFact(fact_id="MR-006-F1", category="positioning",
                              statement="Anchorpoint AI positions as 'accuracy-first', trading latency for citation-backed answers.",
                              evidence_ids=[e6])],
    )

    # MR-007: verified differentiator
    e7 = b.ev(
        LUMEN_CASCADE, "differentiators", "reputable_news",
        "https://technewsdaily.example.com/lumen-cascade-offline-mode",
        "TechNewsDaily -- Lumen Cascade Ships Offline-First Mode",
        "Lumen Cascade shipped an offline-first mode this quarter, letting field teams keep "
        "using the app without connectivity and sync changes once back online. Reviewers "
        "note this is a capability none of Lumen Cascade's closest competitors currently "
        "offer, making it a genuine differentiator rather than marketing language.",
        published_at="2026-05-02",
    )
    b.scenario(
        "MR-007", PIPELINE_HARBOR, [LUMEN_CASCADE],
        "What is a verified differentiator for Lumen Cascade versus its competitors?",
        "differentiators", "PASS", "faithfulness", difficulty="medium",
        expected_claims=["Lumen Cascade's offline-first mode is a differentiator not offered by its closest competitors."],
        relevant_evidence_ids=[e7], required_evidence_ids=[e7],
        gold_facts=[GoldFact(fact_id="MR-007-F1", category="differentiators",
                              statement="Lumen Cascade differentiates with an offline-first mode absent from close competitors.",
                              evidence_ids=[e7])],
    )

    # MR-008: product announcement
    e8 = b.ev(
        DRIFTWOOD, "announcements", "official",
        "https://driftwoodsystems.com/blog/introducing-workflow-builder",
        "Driftwood Systems -- Introducing Workflow Builder",
        "Driftwood Systems announced general availability of its no-code Workflow Builder, "
        "letting customers chain triggers and actions across connected apps without writing "
        "scripts. The announcement states the feature is available on Growth and above plans "
        "starting this month.",
        published_at="2026-05-20",
    )
    b.scenario(
        "MR-008", PIPELINE_HARBOR, [DRIFTWOOD],
        "What did Driftwood Systems recently announce?",
        "announcements", "PASS", "faithfulness", difficulty="easy",
        expected_claims=["Driftwood Systems announced general availability of a no-code Workflow Builder."],
        relevant_evidence_ids=[e8], required_evidence_ids=[e8],
        gold_facts=[GoldFact(fact_id="MR-008-F1", category="announcements",
                              statement="Driftwood Systems announced GA of its no-code Workflow Builder.",
                              evidence_ids=[e8])],
    )

    # MR-009: recent news
    e9 = b.ev(
        HARBORLIGHT, "recent_news", "reputable_news",
        "https://cloudwire.example.com/harborlight-series-b",
        "CloudWire -- Harborlight Cloud Raises $40M Series B",
        "Harborlight Cloud raised a $40M Series B led by a growth-stage fund, which it says "
        "will fund expansion into the European market and doubling of its engineering team "
        "over the next 18 months. The round closed last month according to the company.",
        published_at="2026-05-28",
    )
    b.scenario(
        "MR-009", PIPELINE_HARBOR, [HARBORLIGHT],
        "What recent news is there about Harborlight Cloud?",
        "recent_news", "PASS", "faithfulness", difficulty="easy",
        expected_claims=["Harborlight Cloud raised a $40M Series B to fund European expansion and engineering growth."],
        relevant_evidence_ids=[e9], required_evidence_ids=[e9],
        gold_facts=[GoldFact(fact_id="MR-009-F1", category="recent_news",
                              statement="Harborlight Cloud raised a $40M Series B (2026-05).",
                              evidence_ids=[e9])],
    )

    # MR-010: free trial availability
    e10 = b.ev(
        NORTHWIND, "free_trial", "official",
        "https://northwindanalytics.io/trial",
        "Northwind Analytics -- Start Your Free Trial",
        "Northwind Analytics offers a 14-day free trial with full feature access and no credit "
        "card required to start. At the end of the trial, accounts are downgraded to a "
        "read-only state rather than being auto-billed.",
        published_at="2026-04-05",
    )
    b.scenario(
        "MR-010", PIPELINE_HARBOR, [NORTHWIND],
        "Does Northwind Analytics offer a free trial?",
        "free_trial", "PASS", "faithfulness", difficulty="easy",
        expected_claims=["Northwind Analytics offers a 14-day free trial with no credit card required."],
        relevant_evidence_ids=[e10], required_evidence_ids=[e10],
        gold_facts=[GoldFact(fact_id="MR-010-F1", category="free_trial",
                              statement="Northwind Analytics offers a 14-day free trial, no card required.",
                              evidence_ids=[e10])],
    )

    # MR-011: customer review
    e11 = b.ev(
        VANTAGE_LOOP, "customer_reviews", "review",
        "https://peerreviews.example.com/vantage-loop/review-8821",
        "PeerReviews -- Vantage Loop Review",
        "A verified reviewer on a third-party review site rated Vantage Loop 4.5/5, praising "
        "the onboarding speed and API documentation, while noting that the mobile app lags "
        "behind the desktop experience in feature parity.",
        published_at="2026-03-22",
    )
    b.scenario(
        "MR-011", PIPELINE_HARBOR, [VANTAGE_LOOP],
        "What do customer reviews say about Vantage Loop?",
        "customer_reviews", "PASS", "faithfulness", difficulty="easy",
        expected_claims=["A verified reviewer rated Vantage Loop 4.5/5, citing fast onboarding but a weaker mobile app."],
        relevant_evidence_ids=[e11], required_evidence_ids=[e11],
        gold_facts=[GoldFact(fact_id="MR-011-F1", category="customer_reviews",
                              statement="Vantage Loop rated 4.5/5 by a verified reviewer; mobile app lags desktop.",
                              evidence_ids=[e11])],
    )

    # MR-012: notable customer
    e12 = b.ev(
        COBALT_MERIDIAN, "notable_customers", "official",
        "https://cobaltmeridian.com/customers/case-study-globex",
        "Cobalt Meridian -- Customer Story: Globex Retail Group",
        "Cobalt Meridian's case study names Globex Retail Group, a mid-size retail chain, as a "
        "customer using the platform to consolidate reporting across 120 stores. The case "
        "study includes a named quote attributed to Globex's VP of Operations.",
        published_at="2026-02-14",
    )
    b.scenario(
        "MR-012", PIPELINE_HARBOR, [COBALT_MERIDIAN],
        "Which notable customers does Cobalt Meridian have?",
        "notable_customers", "PASS", "faithfulness", difficulty="easy",
        expected_claims=["Globex Retail Group is a named Cobalt Meridian customer, per an official case study."],
        relevant_evidence_ids=[e12], required_evidence_ids=[e12],
        gold_facts=[GoldFact(fact_id="MR-012-F1", category="notable_customers",
                              statement="Globex Retail Group is a named Cobalt Meridian customer.",
                              evidence_ids=[e12])],
    )

    # MR-013: company description
    e13 = b.ev(
        FERNBRIDGE, "company_description", "official",
        "https://fernbridgedata.com/about",
        "Fernbridge Data -- About Us",
        "Fernbridge Data is a data-integration company founded to help revenue teams unify "
        "customer data scattered across CRMs, billing systems, and support tools into a "
        "single queryable layer, without requiring a data engineer to maintain pipelines.",
        published_at="2026-01-05",
    )
    b.scenario(
        "MR-013", PIPELINE_HARBOR, [FERNBRIDGE],
        "What does Fernbridge Data do, in its own words?",
        "company_description", "PASS", "faithfulness", difficulty="easy",
        expected_claims=["Fernbridge Data unifies customer data from CRMs, billing, and support tools into one queryable layer."],
        relevant_evidence_ids=[e13], required_evidence_ids=[e13],
        gold_facts=[GoldFact(fact_id="MR-013-F1", category="company_description",
                              statement="Fernbridge Data unifies CRM/billing/support data into one queryable layer.",
                              evidence_ids=[e13])],
    )

    # MR-014: multiple corroborating sources
    e14a = b.ev(
        SOLACE_METRICS, "core_features", "official",
        "https://solacemetrics.com/features/forecasting",
        "Solace Metrics -- Forecasting",
        "Solace Metrics includes built-in revenue forecasting using historical pipeline data, "
        "with configurable confidence intervals shown alongside each forecast line.",
        published_at="2026-02-01",
    )
    e14b = b.ev(
        SOLACE_METRICS, "core_features", "reputable_news",
        "https://saastoday.example.com/solace-metrics-forecasting-review",
        "SaaSToday -- Hands-on With Solace Metrics Forecasting",
        "Independent testing confirms Solace Metrics' forecasting module produces confidence "
        "intervals derived from historical pipeline trends, matching the vendor's own "
        "documentation of the feature.",
        published_at="2026-02-10",
    )
    e14c = b.ev(
        SOLACE_METRICS, "core_features", "review",
        "https://peerreviews.example.com/solace-metrics/review-4410",
        "PeerReviews -- Solace Metrics Review",
        "A verified user review corroborates that Solace Metrics' forecasting feature works "
        "as advertised, calling out the confidence-interval display as genuinely useful for "
        "quarterly planning.",
        published_at="2026-02-18",
    )
    b.scenario(
        "MR-014", PIPELINE_HARBOR, [SOLACE_METRICS],
        "Is Solace Metrics' revenue forecasting feature corroborated by independent sources?",
        "core_features", "PASS", "faithfulness", difficulty="medium",
        expected_claims=["Solace Metrics' revenue forecasting with confidence intervals is corroborated by an official source, independent press, and a user review."],
        relevant_evidence_ids=[e14a, e14b, e14c], required_evidence_ids=[e14a, e14b, e14c],
        gold_facts=[GoldFact(fact_id="MR-014-F1", category="core_features",
                              statement="Solace Metrics offers revenue forecasting with confidence intervals, confirmed by 3 independent sources.",
                              evidence_ids=[e14a, e14b, e14c])],
    )

    # MR-015: successful multi-competitor analysis
    e15a = b.ev(
        NORTHWIND, "pricing", "official",
        "https://northwindanalytics.io/pricing-2026",
        "Northwind Analytics -- 2026 Pricing",
        "Northwind Analytics' current self-serve plan remains $79/seat/month as of this "
        "quarter's pricing page refresh, unchanged from the prior update.",
        published_at="2026-05-01",
    )
    e15b = b.ev(
        VANTAGE_LOOP, "pricing", "official",
        "https://vantageloop.com/plans-2026",
        "Vantage Loop -- 2026 Plans",
        "Vantage Loop's Growth tier remains $99/month as of this quarter, with the same "
        "20-user cap and API access as previously published.",
        published_at="2026-05-03",
    )
    b.scenario(
        "MR-015", PIPELINE_HARBOR, [NORTHWIND, VANTAGE_LOOP],
        "How do Northwind Analytics and Vantage Loop compare on pricing this quarter?",
        "pricing", "PASS", "ground_truth_coverage", difficulty="medium",
        expected_claims=[
            "Northwind Analytics charges $79/seat/month.",
            "Vantage Loop's Growth tier is $99/month for up to 20 users.",
        ],
        relevant_evidence_ids=[e15a, e15b], required_evidence_ids=[e15a, e15b],
        gold_facts=[
            GoldFact(fact_id="MR-015-F1", category="pricing",
                      statement="Northwind Analytics: $79/seat/month.", evidence_ids=[e15a]),
            GoldFact(fact_id="MR-015-F2", category="pricing",
                      statement="Vantage Loop Growth tier: $99/month, 20 users.", evidence_ids=[e15b]),
        ],
    )

    _build_retrieval(b)
    _build_red_flag(b)
    _build_missing_info(b)
    _build_conflict(b)
    _build_coverage_freshness(b)
    _build_cost(b)
    _build_temporal(b)
    _build_resilience(b)

    return b


def _build_retrieval(b: Builder) -> None:
    # MR-016: irrelevant blog posts mixed with pricing evidence
    true1 = b.ev(
        ANCHORPOINT, "pricing", "official",
        "https://anchorpoint.ai/pricing",
        "Anchorpoint AI -- Pricing",
        "Anchorpoint AI charges $149 per month for its Pro plan, which includes unlimited "
        "queries and priority support. A free tier caps usage at 100 queries per month.",
        published_at="2026-04-10",
    )
    b.ev(
        ANCHORPOINT, "blog", "blog",
        "https://randomtechblog.example.com/5-ai-tools-worth-trying",
        "5 AI Tools Worth Trying This Year",
        "This roundup blog post mentions Anchorpoint AI in passing alongside four unrelated "
        "tools, with a one-line description and no pricing details, focused mostly on the "
        "author's personal productivity habits.",
        published_at="2025-08-01",
    )
    b.ev(
        ANCHORPOINT, "blog", "blog",
        "https://randomtechblog.example.com/my-morning-routine",
        "My Morning Routine as a Remote Founder",
        "An unrelated lifestyle blog post about the author's morning routine that briefly "
        "namedrops several SaaS tools, including Anchorpoint AI, without discussing pricing "
        "or features in any depth.",
        published_at="2025-06-15",
    )
    b.ev(
        ANCHORPOINT, "community", "community",
        "https://forum.example.com/thread/anchorpoint-vs-alternatives",
        "Forum: Anchorpoint vs alternatives?",
        "A community forum thread where users speculate about Anchorpoint AI's pricing "
        "without citing any source, with several conflicting guesses and no confirmation "
        "from the company.",
        published_at="2025-09-20",
    )
    b.scenario(
        "MR-016", PIPELINE_HARBOR, [ANCHORPOINT],
        "What does Anchorpoint AI charge for its Pro plan?",
        "pricing", "RETRIEVAL", "retrieval_precision_at_5", difficulty="medium", top_k=5,
        relevant_evidence_ids=[true1],
        required_evidence_ids=[true1],
    )

    # MR-017: similar company names
    true2 = b.ev(
        LUMEN_CASCADE, "pricing", "official",
        "https://lumencascade.com/pricing",
        "Lumen Cascade -- Pricing",
        "Lumen Cascade's standard plan costs $89 per month per workspace, with unlimited "
        "seats included and usage-based add-ons billed separately.",
        published_at="2026-03-30",
    )
    b.ev(
        "Lumen Cascadia", "pricing", "low_authority",
        "https://directory.example.com/lumen-cascadia-listing",
        "Business Directory: Lumen Cascadia LLC",
        "A directory listing for Lumen Cascadia LLC, an unrelated regional consulting firm "
        "with a similar name, listing a flat consulting rate of $200/hour -- not the same "
        "company as the software vendor Lumen Cascade.",
        published_at="2024-11-01",
    )
    b.ev(
        "Lumen Cascade Partners", "pricing", "low_authority",
        "https://oldindex.example.com/lumen-cascade-partners",
        "Lumen Cascade Partners -- Financial Advisory",
        "An unrelated financial advisory firm called Lumen Cascade Partners, sharing part of "
        "the name but operating in a different industry, with no software pricing to speak of.",
        published_at="2023-05-12",
    )
    b.scenario(
        "MR-017", PIPELINE_HARBOR, [LUMEN_CASCADE],
        "What is Lumen Cascade's monthly pricing?",
        "pricing", "RETRIEVAL", "retrieval_precision_at_5", difficulty="hard", top_k=5,
        relevant_evidence_ids=[true2],
        required_evidence_ids=[true2],
    )

    # MR-018: shared product names
    true3 = b.ev(
        DRIFTWOOD, "core_features", "documentation",
        "https://docs.driftwoodsystems.com/features/pulse",
        "Driftwood Systems -- Pulse Monitoring",
        "Driftwood Systems' 'Pulse' feature is a real-time uptime monitor that alerts teams "
        "via Slack or PagerDuty within 30 seconds of a detected outage.",
        published_at="2026-02-25",
    )
    b.ev(
        "Vitalis Health", "core_features", "blog",
        "https://healthblog.example.com/pulse-wearable-review",
        "Pulse Wearable Review -- Vitalis Health",
        "A review of 'Pulse', a fitness wearable made by an unrelated health-tech company, "
        "measuring heart rate and sleep -- unrelated to any software monitoring product.",
        published_at="2025-07-04",
    )
    b.ev(
        "Meridian Finance", "core_features", "blog",
        "https://fintechnews.example.com/pulse-budgeting-app",
        "Pulse Budgeting App Launches",
        "An unrelated budgeting app also called 'Pulse', launched by a fintech startup, with "
        "no connection to uptime monitoring or Driftwood Systems.",
        published_at="2025-10-11",
    )
    b.scenario(
        "MR-018", PIPELINE_HARBOR, [DRIFTWOOD],
        "What does Driftwood Systems' Pulse feature do?",
        "core_features", "RETRIEVAL", "retrieval_precision_at_5", difficulty="hard", top_k=5,
        relevant_evidence_ids=[true3],
        required_evidence_ids=[true3],
    )

    # MR-019: old pricing ranked above current
    b.ev(
        HARBORLIGHT, "pricing", "low_authority",
        "https://archived-pricing.example.com/harborlight-2024",
        "Archived: Harborlight Cloud Pricing (2024 snapshot)",
        "An archived page snapshot shows Harborlight Cloud's plan at $59/month from 2024 -- "
        "this page has not been updated since and is indexed with high generic authority by "
        "some search engines despite being stale.",
        published_at="2024-06-01",
    )
    current_price = b.ev(
        HARBORLIGHT, "pricing", "official",
        "https://harborlightcloud.com/pricing",
        "Harborlight Cloud -- Current Pricing",
        "Harborlight Cloud's current plan is $89/month, reflecting a price increase that took "
        "effect at the start of this year. This page is the canonical, actively maintained "
        "pricing source.",
        published_at="2026-01-15",
    )
    b.scenario(
        "MR-019", PIPELINE_HARBOR, [HARBORLIGHT],
        "What is Harborlight Cloud's current monthly price?",
        "pricing", "RETRIEVAL", "retrieval_precision_at_5", difficulty="hard", top_k=5,
        relevant_evidence_ids=[current_price],
        required_evidence_ids=[current_price],
    )

    # MR-020: generic industry articles
    true4 = b.ev(
        COBALT_MERIDIAN, "differentiators", "official",
        "https://cobaltmeridian.com/why-us",
        "Cobalt Meridian -- Why Choose Us",
        "Cobalt Meridian differentiates through a proprietary anomaly-detection model tuned "
        "specifically for retail transaction data, reducing false-positive fraud alerts by a "
        "reported 40% versus generic models.",
        published_at="2026-03-05",
    )
    b.ev(
        "Industry Overview", "differentiators", "blog",
        "https://industryinsights.example.com/state-of-analytics-2026",
        "State of the Analytics Industry 2026",
        "A generic industry-trends article discussing analytics software broadly, mentioning "
        "dozens of vendors by name including Cobalt Meridian in a single list, with no "
        "specific claims about any one company's differentiators.",
        published_at="2026-01-01",
    )
    b.ev(
        "Industry Overview", "differentiators", "blog",
        "https://industryinsights.example.com/analytics-market-map",
        "2026 Analytics Market Map",
        "A market-map style article that places many vendors including Cobalt Meridian into "
        "quadrants based on generic axes like 'ease of use' and 'scalability', without citing "
        "any company-specific evidence.",
        published_at="2026-01-05",
    )
    b.scenario(
        "MR-020", PIPELINE_HARBOR, [COBALT_MERIDIAN],
        "What differentiates Cobalt Meridian from other analytics vendors?",
        "differentiators", "RETRIEVAL", "retrieval_precision_at_5", difficulty="medium", top_k=5,
        relevant_evidence_ids=[true4],
        required_evidence_ids=[true4],
    )

    # MR-021: misleading-keyword reviews
    true5 = b.ev(
        SOLACE_METRICS, "customer_reviews", "review",
        "https://peerreviews.example.com/solace-metrics/review-9012",
        "PeerReviews -- Solace Metrics Verified Review",
        "A verified Solace Metrics customer rates the product 4/5, specifically praising the "
        "forecasting module and noting responsive support during onboarding.",
        published_at="2026-04-01",
    )
    b.ev(
        SOLACE_METRICS, "customer_reviews", "review",
        "https://peerreviews.example.com/other-vendor/review-comparing-solace",
        "Review of CompetitorX (mentions Solace Metrics)",
        "A review primarily about an unrelated vendor 'CompetitorX' that mentions 'we also "
        "tried Solace Metrics but switched away' in one sentence, with the bulk of the review "
        "keyworded around Solace Metrics due to how the review site tags mentions.",
        published_at="2025-12-01",
    )
    b.ev(
        SOLACE_METRICS, "customer_reviews", "low_authority",
        "https://spamreviews.example.com/solace-metrics-scam-warning",
        "Is Solace Metrics a Scam? (clickbait)",
        "A low-authority clickbait page with the keyword 'Solace Metrics' stuffed into the "
        "title and text purely for SEO, containing no actual product review content or "
        "verifiable claims.",
        published_at="2025-11-20",
    )
    b.scenario(
        "MR-021", PIPELINE_HARBOR, [SOLACE_METRICS],
        "What do genuine customer reviews say about Solace Metrics?",
        "customer_reviews", "RETRIEVAL", "retrieval_precision_at_5", difficulty="hard", top_k=5,
        relevant_evidence_ids=[true5],
        required_evidence_ids=[true5],
    )

    # MR-022: job postings with product terms
    true6 = b.ev(
        FERNBRIDGE, "core_features", "documentation",
        "https://docs.fernbridgedata.com/features/pipelines",
        "Fernbridge Data Documentation -- Pipelines",
        "Fernbridge Data's pipeline engine supports scheduled and event-triggered data "
        "transformations with a visual DAG editor, and exposes pipeline run history via API.",
        published_at="2026-02-05",
    )
    b.ev(
        FERNBRIDGE, "core_features", "low_authority",
        "https://jobs.example.com/fernbridge-data-senior-pipeline-engineer",
        "Fernbridge Data is hiring: Senior Pipeline Engineer",
        "A job posting describing internal engineering work on 'our pipeline infrastructure "
        "and DAG scheduler', written for engineering candidates and not describing the "
        "customer-facing product feature set.",
        published_at="2026-04-20",
    )
    b.ev(
        FERNBRIDGE, "core_features", "low_authority",
        "https://jobs.example.com/fernbridge-data-platform-engineer",
        "Fernbridge Data is hiring: Platform Engineer",
        "A job posting mentioning 'pipeline reliability' and 'DAG orchestration' as internal "
        "engineering responsibilities, again aimed at job candidates rather than describing "
        "the shipped customer feature.",
        published_at="2026-04-22",
    )
    b.scenario(
        "MR-022", PIPELINE_HARBOR, [FERNBRIDGE],
        "What does Fernbridge Data's customer-facing pipeline feature actually do?",
        "core_features", "RETRIEVAL", "retrieval_precision_at_5", difficulty="hard", top_k=5,
        relevant_evidence_ids=[true6],
        required_evidence_ids=[true6],
    )

    # MR-023: partner vs official docs
    true7 = b.ev(
        NORTHWIND, "core_features", "documentation",
        "https://docs.northwindanalytics.io/api/rate-limits",
        "Northwind Analytics Documentation -- API Rate Limits",
        "Northwind Analytics' official API documentation states the rate limit is 600 "
        "requests per minute on the Business plan, with a 429 response and Retry-After "
        "header returned when exceeded.",
        published_at="2026-03-10",
    )
    b.ev(
        "Northwind Reseller Co", "core_features", "partner",
        "https://northwindreseller.example.com/faq",
        "Northwind Reseller Co -- FAQ",
        "A reseller partner's FAQ page states the API rate limit is 'around 500 requests per "
        "minute', a paraphrased and slightly inaccurate secondhand figure not sourced from "
        "Northwind Analytics' own documentation.",
        published_at="2025-09-01",
    )
    b.scenario(
        "MR-023", PIPELINE_HARBOR, [NORTHWIND],
        "What is Northwind Analytics' official API rate limit?",
        "core_features", "RETRIEVAL", "retrieval_precision_at_5", difficulty="medium", top_k=5,
        relevant_evidence_ids=[true7],
        required_evidence_ids=[true7],
    )

    # MR-024: duplicate content
    true8 = b.ev(
        VANTAGE_LOOP, "free_trial", "official",
        "https://vantageloop.com/trial",
        "Vantage Loop -- Free Trial",
        "Vantage Loop offers a 21-day free trial of the Growth tier, requiring a work email "
        "but no credit card, with in-app prompts to upgrade as the trial nears expiration.",
        published_at="2026-04-15",
    )
    b.ev(
        VANTAGE_LOOP, "free_trial", "blog",
        "https://mirror1.example.com/vantage-loop-trial",
        "Vantage Loop -- Free Trial (mirrored)",
        "Vantage Loop offers a 21-day free trial of the Growth tier, requiring a work email "
        "but no credit card, with in-app prompts to upgrade as the trial nears expiration.",
        published_at="2026-04-16",
    )
    b.ev(
        VANTAGE_LOOP, "free_trial", "blog",
        "https://mirror2.example.com/vantage-loop-trial-copy",
        "Vantage Loop -- Free Trial (syndicated copy)",
        "Vantage Loop offers a 21-day free trial of the Growth tier, requiring a work email "
        "but no credit card, with in-app prompts to upgrade as the trial nears expiration.",
        published_at="2026-04-17",
    )
    b.scenario(
        "MR-024", PIPELINE_HARBOR, [VANTAGE_LOOP],
        "Does Vantage Loop offer a free trial, and on what terms?",
        "free_trial", "RETRIEVAL", "retrieval_recall_at_5", difficulty="medium", top_k=5,
        relevant_evidence_ids=[true8],
        required_evidence_ids=[true8],
    )

    # MR-025: weak third-party evidence ranked above authoritative sources
    weak1 = b.ev(
        ANCHORPOINT, "positioning", "low_authority",
        "https://aggregator.example.com/anchorpoint-summary",
        "Aggregator Summary: Anchorpoint AI",
        "An auto-generated aggregator page summarizing Anchorpoint AI from scraped snippets, "
        "asserting the company 'focuses on speed above all else' -- which contradicts the "
        "company's own stated positioning and is not independently verified.",
        published_at="2025-05-01",
    )
    authoritative1 = b.ev(
        ANCHORPOINT, "positioning", "official",
        "https://anchorpoint.ai/about",
        "Anchorpoint AI -- About",
        "Anchorpoint AI states its explicit priority is accuracy and verifiability over raw "
        "response speed, and that this tradeoff is a deliberate design choice reflected "
        "throughout the product.",
        published_at="2026-01-20",
    )
    b.scenario(
        "MR-025", PIPELINE_HARBOR, [ANCHORPOINT],
        "How does Anchorpoint AI describe its own market positioning?",
        "positioning", "RETRIEVAL", "retrieval_precision_at_5", difficulty="hard", top_k=5,
        relevant_evidence_ids=[authoritative1],
        required_evidence_ids=[authoritative1],
    )
    # weak1 exists in the corpus purely as a distractor for MR-025's retrieval scoring.
    _ = weak1


def _build_red_flag(b: Builder) -> None:
    # MR-026: significant price increase
    e = b.ev(
        HARBORLIGHT, "pricing", "reputable_news",
        "https://cloudwire.example.com/harborlight-price-hike",
        "CloudWire -- Harborlight Cloud Raises Prices 50%",
        "Harborlight Cloud notified customers of a 50% price increase effective next billing "
        "cycle, moving its standard plan from $59/month to $89/month, citing rising "
        "infrastructure costs. Several customers on social media expressed frustration at the "
        "size of the increase.",
        published_at="2026-01-10",
    )
    b.scenario(
        "MR-026", PIPELINE_HARBOR, [HARBORLIGHT],
        "Has Harborlight Cloud made any significant pricing changes recently?",
        "pricing", "RED_FLAG", "red_flag_recall", difficulty="medium",
        relevant_evidence_ids=[e], required_evidence_ids=[e],
        expected_red_flags=[GoldRedFlag(
            red_flag_id="RF-026-1", type="price_increase",
            description="Harborlight Cloud raised its standard plan price 50% ($59 to $89/month).",
            severity="medium", expected_evidence_ids=[e], is_critical=False,
            expected_agent_response="Flag the 50% price increase as a material red flag with the cited evidence, without inventing a reason beyond what the source states.",
        )],
    )

    # MR-027: product discontinuation
    e = b.ev(
        VANTAGE_LOOP, "announcements", "official",
        "https://vantageloop.com/blog/sunsetting-legacy-reports",
        "Vantage Loop -- Sunsetting the Legacy Reports Module",
        "Vantage Loop announced it will fully discontinue its Legacy Reports module in three "
        "months, with no replacement offered for customers who relied on its custom export "
        "format. Affected customers must migrate to the new Dashboards module manually.",
        published_at="2026-03-01",
    )
    b.scenario(
        "MR-027", PIPELINE_HARBOR, [VANTAGE_LOOP],
        "Is Vantage Loop discontinuing any product modules?",
        "announcements", "RED_FLAG", "critical_red_flag_recall", difficulty="medium",
        relevant_evidence_ids=[e], required_evidence_ids=[e],
        expected_red_flags=[GoldRedFlag(
            red_flag_id="RF-027-1", type="product_discontinuation",
            description="Vantage Loop is discontinuing its Legacy Reports module with no replacement for the custom export format.",
            severity="high", expected_evidence_ids=[e], is_critical=True,
            expected_agent_response="Flag the discontinuation as critical since affected customers have no migration path, citing the official announcement.",
        )],
    )

    # MR-028: security incident
    e = b.ev(
        NORTHWIND, "recent_news", "reputable_news",
        "https://securitywire.example.com/northwind-breach-disclosure",
        "SecurityWire -- Northwind Analytics Discloses Data Exposure",
        "Northwind Analytics disclosed that a misconfigured storage bucket exposed a subset "
        "of customer dashboard metadata for approximately 11 days before being discovered "
        "and secured. The company says no passwords or payment data were involved, and it "
        "has notified affected customers directly.",
        published_at="2026-02-18",
    )
    b.scenario(
        "MR-028", PIPELINE_HARBOR, [NORTHWIND],
        "Has Northwind Analytics had any security incidents?",
        "recent_news", "RED_FLAG", "critical_red_flag_recall", difficulty="hard",
        relevant_evidence_ids=[e], required_evidence_ids=[e],
        expected_red_flags=[GoldRedFlag(
            red_flag_id="RF-028-1", type="security_incident",
            description="Northwind Analytics disclosed a data exposure incident affecting customer dashboard metadata for ~11 days.",
            severity="critical", expected_evidence_ids=[e], is_critical=True,
            expected_agent_response="Flag the disclosed security incident as critical, citing the source, and note the company's stated scope (metadata only, no passwords/payment data) without overstating it.",
        )],
    )

    # MR-029: major layoffs/restructuring
    e = b.ev(
        DRIFTWOOD, "recent_news", "reputable_news",
        "https://cloudwire.example.com/driftwood-layoffs",
        "CloudWire -- Driftwood Systems Cuts 18% of Staff",
        "Driftwood Systems laid off approximately 18% of its workforce as part of a "
        "restructuring aimed at extending its cash runway, according to an internal memo "
        "reviewed by the outlet. The company says core product teams were largely spared.",
        published_at="2026-04-05",
    )
    b.scenario(
        "MR-029", PIPELINE_HARBOR, [DRIFTWOOD],
        "Has Driftwood Systems undergone layoffs or restructuring recently?",
        "recent_news", "RED_FLAG", "red_flag_recall", difficulty="medium",
        relevant_evidence_ids=[e], required_evidence_ids=[e],
        expected_red_flags=[GoldRedFlag(
            red_flag_id="RF-029-1", type="layoffs",
            description="Driftwood Systems laid off about 18% of staff as part of a cash-runway-extending restructuring.",
            severity="medium", expected_evidence_ids=[e], is_critical=False,
            expected_agent_response="Flag the layoffs as a red flag with the cited scope, without speculating about product impact beyond what the source states.",
        )],
    )

    # MR-030: regulatory/legal issue
    e = b.ev(
        SOLACE_METRICS, "recent_news", "regulatory",
        "https://regulatorwatch.example.com/solace-metrics-inquiry",
        "RegulatorWatch -- Data Protection Authority Opens Inquiry Into Solace Metrics",
        "A regional data protection authority opened a formal inquiry into Solace Metrics' "
        "data retention practices following user complaints. The inquiry is ongoing and no "
        "findings or penalties have been issued as of this filing.",
        published_at="2026-03-25",
    )
    b.scenario(
        "MR-030", PIPELINE_HARBOR, [SOLACE_METRICS],
        "Is Solace Metrics facing any regulatory or legal issues?",
        "recent_news", "RED_FLAG", "critical_red_flag_recall", difficulty="hard",
        relevant_evidence_ids=[e], required_evidence_ids=[e],
        expected_red_flags=[GoldRedFlag(
            red_flag_id="RF-030-1", type="regulatory_inquiry",
            description="A data protection authority opened an unresolved inquiry into Solace Metrics' data retention practices.",
            severity="high", expected_evidence_ids=[e], is_critical=True,
            expected_agent_response="Flag the open regulatory inquiry as critical given it is unresolved, citing the source and being explicit that no findings have been issued yet.",
        )],
    )

    # MR-031: significant customer complaints/churn
    e = b.ev(
        COBALT_MERIDIAN, "customer_reviews", "review",
        "https://peerreviews.example.com/cobalt-meridian/aggregate-trend",
        "PeerReviews -- Cobalt Meridian Rating Trend",
        "Cobalt Meridian's average review rating dropped from 4.3 to 3.1 over two quarters, "
        "with a spike in complaints specifically about slow support response times and "
        "several verified reviewers stating they were cancelling their subscriptions.",
        published_at="2026-04-12",
    )
    b.scenario(
        "MR-031", PIPELINE_HARBOR, [COBALT_MERIDIAN],
        "Are there signs of significant customer churn or complaints for Cobalt Meridian?",
        "customer_reviews", "RED_FLAG", "red_flag_recall", difficulty="medium",
        relevant_evidence_ids=[e], required_evidence_ids=[e],
        expected_red_flags=[GoldRedFlag(
            red_flag_id="RF-031-1", type="customer_churn",
            description="Cobalt Meridian's review rating dropped from 4.3 to 3.1 over two quarters with reported cancellations tied to slow support.",
            severity="medium", expected_evidence_ids=[e], is_critical=False,
            expected_agent_response="Flag the rating decline and cited cancellations as a churn-related red flag, grounded in the review-trend evidence.",
        )],
    )

    # MR-032: feature deprecation
    e = b.ev(
        FERNBRIDGE, "announcements", "documentation",
        "https://docs.fernbridgedata.com/changelog/2026-04",
        "Fernbridge Data Changelog -- April 2026",
        "The April changelog marks the legacy CSV export endpoint as deprecated, with removal "
        "planned in a future release; customers are directed to migrate to the new streaming "
        "export API before the deprecated endpoint is removed.",
        published_at="2026-04-30",
    )
    b.scenario(
        "MR-032", PIPELINE_HARBOR, [FERNBRIDGE],
        "Has Fernbridge Data deprecated any features recently?",
        "announcements", "RED_FLAG", "red_flag_recall", difficulty="easy",
        relevant_evidence_ids=[e], required_evidence_ids=[e],
        expected_red_flags=[GoldRedFlag(
            red_flag_id="RF-032-1", type="feature_deprecation",
            description="Fernbridge Data deprecated its legacy CSV export endpoint in favor of a new streaming export API.",
            severity="low", expected_evidence_ids=[e], is_critical=False,
            expected_agent_response="Flag the deprecation as low severity with a migration path already offered, citing the changelog.",
        )],
    )

    # MR-033: acquisition creating product uncertainty
    e = b.ev(
        LUMEN_CASCADE, "recent_news", "reputable_news",
        "https://cloudwire.example.com/lumen-cascade-acquired",
        "CloudWire -- Lumen Cascade Acquired by Meridian Holdings",
        "Lumen Cascade has been acquired by Meridian Holdings, a larger enterprise software "
        "conglomerate. The acquiring company has not yet announced its plans for Lumen "
        "Cascade's standalone product roadmap, leaving existing customers uncertain about "
        "long-term support.",
        published_at="2026-05-10",
    )
    b.scenario(
        "MR-033", PIPELINE_HARBOR, [LUMEN_CASCADE],
        "Has Lumen Cascade been acquired, and what does that mean for its product?",
        "recent_news", "RED_FLAG", "red_flag_recall", difficulty="medium",
        relevant_evidence_ids=[e], required_evidence_ids=[e],
        expected_red_flags=[GoldRedFlag(
            red_flag_id="RF-033-1", type="acquisition_uncertainty",
            description="Lumen Cascade was acquired by Meridian Holdings with no announced roadmap plans, creating product continuity uncertainty.",
            severity="medium", expected_evidence_ids=[e], is_critical=False,
            expected_agent_response="Flag the acquisition and note the roadmap uncertainty explicitly rather than assuming continuity or discontinuation.",
        )],
    )


def _build_missing_info(b: Builder) -> None:
    # MR-034: no public pricing
    b.scenario(
        "MR-034", PIPELINE_HARBOR, [DRIFTWOOD],
        "What does Driftwood Systems charge for its Enterprise plan?",
        "pricing", "MISSING_INFO", "unsupported_claim_rate", difficulty="medium",
        relevant_evidence_ids=[], required_evidence_ids=[],
        expected_unknowns=["Not publicly available", "Unknown"],
    )

    # MR-035: no free-trial info
    b.scenario(
        "MR-035", PIPELINE_HARBOR, [COBALT_MERIDIAN],
        "Does Cobalt Meridian offer a free trial?",
        "free_trial", "MISSING_INFO", "unsupported_claim_rate", difficulty="medium",
        relevant_evidence_ids=[], required_evidence_ids=[],
        expected_unknowns=["Not publicly available", "No reliable evidence found"],
    )

    # MR-036: no reliable customer evidence
    low1 = b.ev(
        HARBORLIGHT, "customer_reviews", "low_authority",
        "https://randomforum.example.com/thread/harborlight-anyone-used-it",
        "Random Forum: Anyone used Harborlight Cloud?",
        "An anonymous, unverified forum post claiming to have used Harborlight Cloud 'a "
        "while back' with vague, unsubstantiated complaints and no way to confirm the "
        "poster's identity or actual usage.",
        published_at="2025-01-01",
    )
    b.scenario(
        "MR-036", PIPELINE_HARBOR, [HARBORLIGHT],
        "What do reliable customer reviews say about Harborlight Cloud?",
        "customer_reviews", "MISSING_INFO", "unsupported_claim_rate", difficulty="hard",
        relevant_evidence_ids=[], required_evidence_ids=[],
        expected_unknowns=["Insufficient evidence", "No reliable evidence found"],
    )
    _ = low1

    # MR-037: only low-quality sources
    low2 = b.ev(
        ANCHORPOINT, "notable_customers", "low_authority",
        "https://spamdirectory.example.com/anchorpoint-clients-maybe",
        "Unverified: Companies That Might Use Anchorpoint AI",
        "An unverified, auto-generated directory page speculating about which companies "
        "might use Anchorpoint AI based on scraped social-media mentions, with no "
        "confirmation from Anchorpoint AI or the named companies.",
        published_at="2025-03-01",
    )
    b.scenario(
        "MR-037", PIPELINE_HARBOR, [ANCHORPOINT],
        "Which notable customers does Anchorpoint AI have?",
        "notable_customers", "MISSING_INFO", "unsupported_claim_rate", difficulty="hard",
        relevant_evidence_ids=[low2], required_evidence_ids=[],
        expected_unknowns=["Insufficient evidence", "Unknown"],
    )

    # MR-038: no recent relevant news
    stale1 = b.ev(
        VANTAGE_LOOP, "recent_news", "blog",
        "https://oldnews.example.com/vantage-loop-2022-launch",
        "Vantage Loop Launches (2022 archive)",
        "An archived article about Vantage Loop's original 2022 product launch -- more than "
        "three years old and not relevant to any recent developments.",
        published_at="2022-06-01",
    )
    b.scenario(
        "MR-038", PIPELINE_HARBOR, [VANTAGE_LOOP],
        "What recent news is there about Vantage Loop in the last quarter?",
        "recent_news", "MISSING_INFO", "unsupported_claim_rate", difficulty="medium",
        relevant_evidence_ids=[], required_evidence_ids=[],
        expected_unknowns=["No reliable evidence found", "Not publicly available"],
    )
    _ = stale1

    # MR-039: evidence doesn't support a claimed feature
    unrelated1 = b.ev(
        NORTHWIND, "core_features", "documentation",
        "https://docs.northwindanalytics.io/features/overview",
        "Northwind Analytics Documentation -- Feature Overview",
        "Northwind Analytics' documented feature set covers dashboards, alerts, and data "
        "connectors; there is no mention anywhere in the documentation of a mobile "
        "offline-editing capability.",
        published_at="2026-03-20",
    )
    b.scenario(
        "MR-039", PIPELINE_HARBOR, [NORTHWIND],
        "Does Northwind Analytics support offline editing on mobile?",
        "core_features", "MISSING_INFO", "unsupported_claim_rate", difficulty="hard",
        relevant_evidence_ids=[unrelated1], required_evidence_ids=[],
        expected_unknowns=["Not publicly available", "Insufficient evidence"],
    )

    # MR-040: source/provider unavailable (simulated fetch failure)
    b.scenario(
        "MR-040", PIPELINE_HARBOR, [SOLACE_METRICS],
        "What is Solace Metrics' current core feature set, per its website?",
        "core_features", "MISSING_INFO", "unsupported_claim_rate", difficulty="medium",
        simulation={"source_unavailable": "solacemetrics.com"},
        relevant_evidence_ids=[], required_evidence_ids=[],
        expected_unknowns=["Not publicly available", "Unknown", "No reliable evidence found"],
    )


def _build_conflict(b: Builder) -> None:
    # MR-041: $99 vs $129 pricing
    a = b.ev(
        DRIFTWOOD, "pricing", "official",
        "https://driftwoodsystems.com/pricing",
        "Driftwood Systems -- Pricing",
        "Driftwood Systems' Growth plan is listed at $99 per month on the current pricing "
        "page, updated this month.",
        published_at="2026-05-15",
    )
    bb = b.ev(
        DRIFTWOOD, "pricing", "review",
        "https://peerreviews.example.com/driftwood-systems/review-3301",
        "PeerReviews -- Driftwood Systems Review",
        "A reviewer states they are paying $129/month for the Growth plan, a figure that "
        "predates the vendor's most recent price adjustment mentioned in their review.",
        published_at="2026-01-20",
    )
    b.scenario(
        "MR-041", PIPELINE_HARBOR, [DRIFTWOOD],
        "What is Driftwood Systems' Growth plan price?",
        "pricing", "CONFLICT", "conflict_resolution", difficulty="medium",
        relevant_evidence_ids=[a, bb], required_evidence_ids=[a, bb],
        expected_conflicts=[GoldConflict(
            field="pricing", value_a="$99/month", value_b="$129/month",
            evidence_ids_a=[a], evidence_ids_b=[bb],
            source_authority_a="official", source_authority_b="review",
            published_at_a="2026-05-15", published_at_b="2026-01-20",
            expected_preferred_value="$99/month",
            expected_resolution_reason="The official, more recently updated pricing page should be preferred over an older third-party review mentioning a stale price.",
        )],
    )

    # MR-042: free trial yes vs no
    a = b.ev(
        FERNBRIDGE, "free_trial", "official",
        "https://fernbridgedata.com/trial",
        "Fernbridge Data -- Free Trial",
        "Fernbridge Data offers a 14-day free trial of its Growth plan, available directly "
        "through self-serve signup.",
        published_at="2026-04-01",
    )
    bb = b.ev(
        FERNBRIDGE, "free_trial", "partner",
        "https://fernbridgereseller.example.com/faq",
        "Fernbridge Reseller FAQ",
        "A reseller's FAQ page states Fernbridge Data 'does not offer a free trial, only a "
        "demo call with sales', which the reseller may not have updated after Fernbridge "
        "changed its self-serve policy.",
        published_at="2025-08-01",
    )
    b.scenario(
        "MR-042", PIPELINE_HARBOR, [FERNBRIDGE],
        "Does Fernbridge Data offer a free trial?",
        "free_trial", "CONFLICT", "conflict_resolution", difficulty="medium",
        relevant_evidence_ids=[a, bb], required_evidence_ids=[a, bb],
        expected_conflicts=[GoldConflict(
            field="free_trial", value_a="Yes, 14-day free trial", value_b="No, demo call only",
            evidence_ids_a=[a], evidence_ids_b=[bb],
            source_authority_a="official", source_authority_b="partner",
            published_at_a="2026-04-01", published_at_b="2025-08-01",
            expected_preferred_value="Yes, 14-day free trial",
            expected_resolution_reason="The official, more recent source should be preferred over a stale partner FAQ.",
        )],
    )

    # MR-043: feature available vs deprecated
    a = b.ev(
        VANTAGE_LOOP, "core_features", "documentation",
        "https://docs.vantageloop.com/features/legacy-export",
        "Vantage Loop Documentation -- Legacy Export (archived version)",
        "An archived documentation snapshot lists the Legacy Export feature as fully "
        "supported and available on all plans.",
        published_at="2025-06-01",
    )
    bb = b.ev(
        VANTAGE_LOOP, "core_features", "documentation",
        "https://docs.vantageloop.com/changelog/2026-03",
        "Vantage Loop Changelog -- March 2026",
        "The March 2026 changelog confirms the Legacy Export feature was fully removed from "
        "all plans, superseded by the new Data Export API.",
        published_at="2026-03-01",
    )
    b.scenario(
        "MR-043", PIPELINE_HARBOR, [VANTAGE_LOOP],
        "Is Vantage Loop's Legacy Export feature still available?",
        "core_features", "CONFLICT", "conflict_resolution", difficulty="medium",
        relevant_evidence_ids=[a, bb], required_evidence_ids=[a, bb],
        expected_conflicts=[GoldConflict(
            field="core_features", value_a="Legacy Export available", value_b="Legacy Export removed/deprecated",
            evidence_ids_a=[a], evidence_ids_b=[bb],
            source_authority_a="documentation", source_authority_b="documentation",
            published_at_a="2025-06-01", published_at_b="2026-03-01",
            expected_preferred_value="Legacy Export removed/deprecated",
            expected_resolution_reason="The more recent changelog supersedes the older archived documentation snapshot.",
        )],
    )

    # MR-044: conflicting employee counts
    a = b.ev(
        HARBORLIGHT, "company_description", "official",
        "https://harborlightcloud.com/about",
        "Harborlight Cloud -- About",
        "Harborlight Cloud states it has 'over 150 employees globally' on its about page.",
        published_at="2026-02-01",
    )
    bb = b.ev(
        HARBORLIGHT, "company_description", "reputable_news",
        "https://cloudwire.example.com/harborlight-profile",
        "CloudWire -- Company Profile: Harborlight Cloud",
        "A press profile independently reports Harborlight Cloud has approximately 90 "
        "employees, based on LinkedIn headcount data at the time of writing.",
        published_at="2025-10-01",
    )
    b.scenario(
        "MR-044", PIPELINE_HARBOR, [HARBORLIGHT],
        "How many employees does Harborlight Cloud have?",
        "company_description", "CONFLICT", "conflict_resolution", difficulty="hard",
        relevant_evidence_ids=[a, bb], required_evidence_ids=[a, bb],
        expected_conflicts=[GoldConflict(
            field="company_description", value_a="150+ employees", value_b="~90 employees",
            evidence_ids_a=[a], evidence_ids_b=[bb],
            source_authority_a="official", source_authority_b="reputable_news",
            published_at_a="2026-02-01", published_at_b="2025-10-01",
            must_remain_unresolved=True, requires_human_review=True,
        )],
    )

    # MR-045: conflicting customer counts
    a = b.ev(
        SOLACE_METRICS, "notable_customers", "official",
        "https://solacemetrics.com/about",
        "Solace Metrics -- About",
        "Solace Metrics' about page states the company serves 'over 2,000 customers "
        "worldwide'.",
        published_at="2026-01-15",
    )
    bb = b.ev(
        SOLACE_METRICS, "notable_customers", "reputable_news",
        "https://saastoday.example.com/solace-metrics-growth-profile",
        "SaaSToday -- Solace Metrics Growth Profile",
        "An independent profile cites Solace Metrics as having roughly 1,200 paying "
        "customers, sourced from a conference talk by the company's CEO.",
        published_at="2025-11-05",
    )
    b.scenario(
        "MR-045", PIPELINE_HARBOR, [SOLACE_METRICS],
        "How many customers does Solace Metrics have?",
        "notable_customers", "CONFLICT", "conflict_resolution", difficulty="hard",
        relevant_evidence_ids=[a, bb], required_evidence_ids=[a, bb],
        expected_conflicts=[GoldConflict(
            field="notable_customers", value_a="2,000+ customers", value_b="~1,200 customers",
            evidence_ids_a=[a], evidence_ids_b=[bb],
            source_authority_a="official", source_authority_b="reputable_news",
            published_at_a="2026-01-15", published_at_b="2025-11-05",
            must_remain_unresolved=True, requires_human_review=True,
        )],
    )

    # MR-046: different launch dates
    a = b.ev(
        ANCHORPOINT, "company_description", "official",
        "https://anchorpoint.ai/about",
        "Anchorpoint AI -- About (company history)",
        "Anchorpoint AI's about page states the company was founded and launched its product "
        "in 2023.",
        published_at="2026-01-01",
    )
    bb = b.ev(
        ANCHORPOINT, "company_description", "blog",
        "https://techarchive.example.com/anchorpoint-early-days",
        "TechArchive -- Anchorpoint AI's Early Days",
        "A retrospective blog post claims Anchorpoint AI actually launched a beta product in "
        "late 2022, a year earlier than the company's own official timeline suggests.",
        published_at="2025-04-01",
    )
    b.scenario(
        "MR-046", PIPELINE_HARBOR, [ANCHORPOINT],
        "When did Anchorpoint AI launch its product?",
        "company_description", "CONFLICT", "conflict_resolution", difficulty="hard",
        relevant_evidence_ids=[a, bb], required_evidence_ids=[a, bb],
        expected_conflicts=[GoldConflict(
            field="company_description", value_a="Launched 2023", value_b="Beta launched late 2022",
            evidence_ids_a=[a], evidence_ids_b=[bb],
            source_authority_a="official", source_authority_b="blog",
            published_at_a="2026-01-01", published_at_b="2025-04-01",
            expected_preferred_value="Launched 2023",
            expected_resolution_reason="The official company account should be preferred over an unverified third-party retrospective, though the discrepancy (beta vs GA) is worth surfacing.",
        )],
    )

    # MR-047: independent company vs acquired
    a = b.ev(
        COBALT_MERIDIAN, "company_description", "official",
        "https://cobaltmeridian.com/about",
        "Cobalt Meridian -- About",
        "Cobalt Meridian's about page describes itself as an independent, privately held "
        "company with no mention of any parent company.",
        published_at="2025-12-01",
    )
    bb = b.ev(
        COBALT_MERIDIAN, "company_description", "reputable_news",
        "https://cloudwire.example.com/cobalt-meridian-acquired-by-vantis",
        "CloudWire -- Cobalt Meridian Acquired by Vantis Group",
        "Cobalt Meridian was acquired by Vantis Group in a deal that closed this quarter, "
        "according to regulatory filings and a joint press statement from both companies.",
        published_at="2026-04-20",
    )
    b.scenario(
        "MR-047", PIPELINE_HARBOR, [COBALT_MERIDIAN],
        "Is Cobalt Meridian an independent company or has it been acquired?",
        "company_description", "CONFLICT", "conflict_resolution", difficulty="medium",
        relevant_evidence_ids=[a, bb], required_evidence_ids=[a, bb],
        expected_conflicts=[GoldConflict(
            field="company_description", value_a="Independent, privately held", value_b="Acquired by Vantis Group",
            evidence_ids_a=[a], evidence_ids_b=[bb],
            source_authority_a="official", source_authority_b="reputable_news",
            published_at_a="2025-12-01", published_at_b="2026-04-20",
            expected_preferred_value="Acquired by Vantis Group",
            expected_resolution_reason="The more recent, independently reported acquisition supersedes the stale 'about' page that predates the deal closing.",
        )],
    )

    # MR-048: official source vs review-site contradiction
    a = b.ev(
        LUMEN_CASCADE, "core_features", "official",
        "https://lumencascade.com/features",
        "Lumen Cascade -- Features",
        "Lumen Cascade's features page states the product includes SOC 2 Type II "
        "certification as of this year.",
        published_at="2026-02-10",
    )
    bb = b.ev(
        LUMEN_CASCADE, "core_features", "review",
        "https://peerreviews.example.com/lumen-cascade/review-5541",
        "PeerReviews -- Lumen Cascade Review",
        "A reviewer states they asked sales for a SOC 2 report and were told the company is "
        "'still in the audit process and not yet certified', contradicting the marketing "
        "page.",
        published_at="2026-03-01",
    )
    b.scenario(
        "MR-048", PIPELINE_HARBOR, [LUMEN_CASCADE],
        "Is Lumen Cascade SOC 2 Type II certified?",
        "core_features", "CONFLICT", "conflict_resolution", difficulty="hard",
        relevant_evidence_ids=[a, bb], required_evidence_ids=[a, bb],
        expected_conflicts=[GoldConflict(
            field="core_features", value_a="SOC 2 Type II certified", value_b="Not yet certified, audit in progress",
            evidence_ids_a=[a], evidence_ids_b=[bb],
            source_authority_a="official", source_authority_b="review",
            published_at_a="2026-02-10", published_at_b="2026-03-01",
            must_remain_unresolved=True, requires_human_review=True,
        )],
    )


def _build_coverage_freshness(b: Builder) -> None:
    subjects = [
        ("MR-049", NORTHWIND),
        ("MR-050", VANTAGE_LOOP),
        ("MR-051", COBALT_MERIDIAN),
        ("MR-052", FERNBRIDGE),
        ("MR-053", SOLACE_METRICS),
    ]
    for scenario_id, company in subjects:
        slug = company.lower().replace(" ", "")
        pricing_ev = b.ev(
            company, "pricing", "official",
            f"https://{slug}.example.com/pricing",
            f"{company} -- Pricing",
            f"{company} publishes a standard plan priced at $99 per month, with a discounted "
            "annual option available at checkout.",
            published_at="2026-03-01",
        )
        features_ev = b.ev(
            company, "core_features", "documentation",
            f"https://docs.{slug}.example.com/features",
            f"{company} Documentation -- Core Features",
            f"{company}'s core feature set includes customizable dashboards, scheduled "
            "reports, and role-based access control, documented in detail for admins.",
            published_at="2026-02-15",
        )
        target_ev = b.ev(
            company, "target_customers", "official",
            f"https://{slug}.example.com/customers",
            f"{company} -- Who It's For",
            f"{company} targets growth-stage B2B companies looking to consolidate reporting "
            "without hiring a dedicated analytics engineer.",
            published_at="2026-01-20",
        )
        positioning_ev = b.ev(
            company, "positioning", "official",
            f"https://{slug}.example.com/about",
            f"{company} -- Positioning",
            f"{company} positions itself as the fastest-to-deploy option in its category, "
            "emphasizing same-day onboarding over deep customization.",
            published_at="2026-02-01",
        )
        differentiators_ev = b.ev(
            company, "differentiators", "reputable_news",
            f"https://saastoday.example.com/{slug}-review",
            f"SaaSToday -- {company} Review",
            f"Independent reviewers note {company}'s standout capability is its "
            "one-click migration tool from spreadsheet-based reporting, a feature "
            "competitors mostly lack.",
            published_at="2026-03-10",
        )
        announcements_ev = b.ev(
            company, "announcements", "official",
            f"https://{slug}.example.com/blog/new-integration",
            f"{company} -- New Integration Announced",
            f"{company} announced a new native integration with a popular billing platform, "
            "available to all paying customers starting this month.",
            published_at="2026-04-01",
        )
        news_ev = b.ev(
            company, "recent_news", "reputable_news",
            f"https://cloudwire.example.com/{slug}-milestone",
            f"CloudWire -- {company} Hits Growth Milestone",
            f"{company} announced it crossed a significant customer-count milestone this "
            "quarter, citing steady growth in its core market segment.",
            published_at="2026-04-15",
        )
        trial_ev = b.ev(
            company, "free_trial", "official",
            f"https://{slug}.example.com/trial",
            f"{company} -- Free Trial",
            f"{company} offers a 14-day free trial with full access to the standard plan's "
            "feature set, no credit card required to begin.",
            published_at="2026-03-20",
        )
        reviews_ev = b.ev(
            company, "customer_reviews", "review",
            f"https://peerreviews.example.com/{slug}/summary",
            f"PeerReviews -- {company} Summary",
            f"{company} holds an average rating of 4.2/5 across verified reviews, with "
            "praise for ease of setup and occasional notes about limited customization.",
            published_at="2026-03-25",
        )
        customers_ev = b.ev(
            company, "notable_customers", "official",
            f"https://{slug}.example.com/customers/case-studies",
            f"{company} -- Case Studies",
            f"{company} publishes a case study naming a mid-size logistics company as a "
            "customer using the platform for weekly operational reporting.",
            published_at="2026-02-20",
        )
        all_ev = [pricing_ev, features_ev, target_ev, positioning_ev, differentiators_ev,
                  announcements_ev, news_ev, trial_ev, reviews_ev, customers_ev]
        gold_facts = [
            GoldFact(fact_id=f"{scenario_id}-F1", category="pricing",
                      statement=f"{company} charges $99/month with an annual discount option.",
                      evidence_ids=[pricing_ev]),
            GoldFact(fact_id=f"{scenario_id}-F2", category="core_features",
                      statement=f"{company} offers dashboards, scheduled reports, and role-based access control.",
                      evidence_ids=[features_ev]),
            GoldFact(fact_id=f"{scenario_id}-F3", category="target_customers",
                      statement=f"{company} targets growth-stage B2B companies without a dedicated analytics engineer.",
                      evidence_ids=[target_ev]),
            GoldFact(fact_id=f"{scenario_id}-F4", category="positioning",
                      statement=f"{company} positions itself as the fastest-to-deploy option, emphasizing same-day onboarding.",
                      evidence_ids=[positioning_ev]),
            GoldFact(fact_id=f"{scenario_id}-F5", category="differentiators",
                      statement=f"{company}'s standout capability is one-click migration from spreadsheets.",
                      evidence_ids=[differentiators_ev]),
            GoldFact(fact_id=f"{scenario_id}-F6", category="announcements",
                      statement=f"{company} announced a new native billing-platform integration.",
                      evidence_ids=[announcements_ev]),
            GoldFact(fact_id=f"{scenario_id}-F7", category="free_trial",
                      statement=f"{company} offers a 14-day free trial, no credit card required.",
                      evidence_ids=[trial_ev]),
        ]
        b.scenario(
            scenario_id, PIPELINE_HARBOR, [company],
            f"Give a full profile of {company} covering pricing, features, positioning, and recent activity.",
            "coverage_freshness", "COVERAGE_FRESHNESS", "ground_truth_coverage", difficulty="medium",
            relevant_evidence_ids=all_ev, required_evidence_ids=all_ev[:7],
            gold_facts=gold_facts,
        )
        _ = (reviews_ev, customers_ev)


def _build_cost(b: Builder) -> None:
    # MR-054: cost projection for a small (2-competitor) research run
    b.scenario(
        "MR-054", PIPELINE_HARBOR, [NORTHWIND, VANTAGE_LOOP],
        "What should a research run analyzing these 2 competitors cost?",
        "cost_projection", "COST", "cost_projection_error", difficulty="medium",
        expected_cost_range=CostRange(min=0.80, max=1.60),
    )

    # MR-055: cost projection for a larger (3-competitor) research run
    b.scenario(
        "MR-055", PIPELINE_HARBOR, [COBALT_MERIDIAN, FERNBRIDGE, SOLACE_METRICS],
        "What should a research run analyzing these 3 competitors cost?",
        "cost_projection", "COST", "cost_projection_error", difficulty="medium",
        expected_cost_range=CostRange(min=1.20, max=2.40),
    )


def _build_temporal(b: Builder) -> None:
    # MR-056: old price vs new price
    old = b.ev(
        NORTHWIND, "pricing", "official",
        "https://web.archive.example.com/northwindanalytics-2025",
        "Northwind Analytics -- Pricing (2025 archive)",
        "An archived snapshot from last year shows Northwind Analytics' self-serve plan "
        "priced at $99 per seat per month.",
        published_at="2025-06-01",
    )
    new = b.ev(
        NORTHWIND, "pricing", "official",
        "https://northwindanalytics.io/pricing",
        "Northwind Analytics -- Current Pricing",
        "Northwind Analytics' current self-serve plan is priced at $149 per seat per month, "
        "reflecting a price change that took effect earlier this year and supersedes any "
        "older published figure.",
        published_at="2026-02-01",
    )
    b.scenario(
        "MR-056", PIPELINE_HARBOR, [NORTHWIND],
        "What is Northwind Analytics' current price, given it changed over the past year?",
        "pricing", "TEMPORAL", "freshness", difficulty="medium",
        relevant_evidence_ids=[old, new], required_evidence_ids=[new],
        expected_current_values={"pricing": "$149/seat/month"},
    )

    # MR-057: deprecated feature vs still-marketed feature
    old_marketing = b.ev(
        VANTAGE_LOOP, "core_features", "blog",
        "https://mirror-cache.example.com/vantage-loop-features-2025",
        "Vantage Loop -- Features (cached 2025 copy)",
        "A cached page from last year still advertises Vantage Loop's 'Classic Reports' "
        "feature as a current, actively supported capability.",
        published_at="2025-09-01",
    )
    deprecation_notice = b.ev(
        VANTAGE_LOOP, "announcements", "documentation",
        "https://docs.vantageloop.com/changelog/2026-01",
        "Vantage Loop Changelog -- January 2026",
        "The January 2026 changelog confirms 'Classic Reports' was deprecated and removed, "
        "replaced entirely by the new Dashboards module -- the cached marketing description "
        "some pages still show is out of date.",
        published_at="2026-01-15",
    )
    b.scenario(
        "MR-057", PIPELINE_HARBOR, [VANTAGE_LOOP],
        "Is Vantage Loop's 'Classic Reports' feature still current?",
        "core_features", "TEMPORAL", "freshness", difficulty="hard",
        relevant_evidence_ids=[old_marketing, deprecation_notice], required_evidence_ids=[deprecation_notice],
        expected_current_values={"core_features": "Classic Reports removed, replaced by Dashboards"},
    )

    # MR-058: updated product positioning over time
    old_pos = b.ev(
        ANCHORPOINT, "positioning", "blog",
        "https://techarchive.example.com/anchorpoint-2024-positioning",
        "TechArchive -- Anchorpoint AI in 2024",
        "In 2024, Anchorpoint AI marketed itself primarily as a 'fast, lightweight' research "
        "assistant, emphasizing speed as its main selling point.",
        published_at="2024-05-01",
    )
    new_pos = b.ev(
        ANCHORPOINT, "positioning", "official",
        "https://anchorpoint.ai/about",
        "Anchorpoint AI -- About (current)",
        "Anchorpoint AI's current messaging has shifted to emphasize accuracy and "
        "verifiability over speed, a repositioning the company made as it matured its "
        "product and target market.",
        published_at="2026-01-20",
    )
    b.scenario(
        "MR-058", PIPELINE_HARBOR, [ANCHORPOINT],
        "How has Anchorpoint AI's market positioning evolved, and what is it now?",
        "positioning", "TEMPORAL", "freshness", difficulty="medium",
        relevant_evidence_ids=[old_pos, new_pos], required_evidence_ids=[new_pos],
        expected_current_values={"positioning": "Accuracy/verifiability-first, not speed-first"},
    )


def _build_resilience(b: Builder) -> None:
    # MR-059: one competitor branch fails while others succeed
    ok_ev = b.ev(
        NORTHWIND, "pricing", "official",
        "https://northwindanalytics.io/pricing",
        "Northwind Analytics -- Pricing",
        "Northwind Analytics charges $79 per seat per month on its self-serve plan, "
        "unchanged this quarter.",
        published_at="2026-05-01",
    )
    b.scenario(
        "MR-059", PIPELINE_HARBOR, [NORTHWIND, HARBORLIGHT],
        "Research these 2 competitors, given that one of their web-research branches will fail.",
        "resilience", "RESILIENCE", "partial_failure_correctness", difficulty="hard",
        simulation={"fail_competitor": HARBORLIGHT},
        relevant_evidence_ids=[ok_ev], required_evidence_ids=[ok_ev],
        expected_unknowns=[
            f"{HARBORLIGHT} branch must be marked failed/partial with no invented facts",
            "Unknown",
        ],
    )

    # MR-060: simulated slow search/LLM/retrieval for latency measurement
    ok_ev2 = b.ev(
        VANTAGE_LOOP, "pricing", "official",
        "https://vantageloop.com/plans",
        "Vantage Loop -- Plans & Pricing",
        "Vantage Loop's Growth tier is $99/month for up to 20 users, unchanged this quarter.",
        published_at="2026-05-01",
    )
    b.scenario(
        "MR-060", PIPELINE_HARBOR, [VANTAGE_LOOP],
        "Research this competitor under simulated slow search/LLM latency conditions.",
        "resilience", "RESILIENCE", "p95_latency_seconds", difficulty="medium",
        simulation={"inject_latency_seconds": 25},
        relevant_evidence_ids=[ok_ev2], required_evidence_ids=[ok_ev2],
    )


def _all_referenced_evidence_ids(scenario: GoldenScenario) -> set[str]:
    ref = scenario.reference_outputs
    ids: set[str] = set()
    ids.update(ref.relevant_evidence_ids)
    ids.update(ref.required_evidence_ids)
    for rf in ref.expected_red_flags:
        ids.update(rf.expected_evidence_ids)
    for c in ref.expected_conflicts:
        ids.update(c.evidence_ids_a)
        ids.update(c.evidence_ids_b)
    for f in ref.gold_facts:
        ids.update(f.evidence_ids)
    return ids


def validate(b: Builder) -> None:
    assert len(b.scenarios) == 60, f"expected 60 scenarios, got {len(b.scenarios)}"

    scenario_ids = [s.inputs.scenario_id for s in b.scenarios]
    expected_ids = [f"MR-{i:03d}" for i in range(1, 61)]
    assert scenario_ids == expected_ids, "scenario_ids must be exactly MR-001..MR-060 in order"
    assert len(set(scenario_ids)) == 60, "scenario_ids must be unique"

    case_type_counts: dict[str, int] = {}
    for s in b.scenarios:
        case_type_counts[s.metadata.case_type] = case_type_counts.get(s.metadata.case_type, 0) + 1

    expected_distribution = {
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
    assert case_type_counts == expected_distribution, (
        f"case_type distribution mismatch: {case_type_counts} != {expected_distribution}"
    )

    evidence_ids = {e.evidence_id for e in b.evidence}
    assert len(evidence_ids) == len(b.evidence), "duplicate evidence_id detected"

    missing: dict[str, list[str]] = {}
    for s in b.scenarios:
        referenced = _all_referenced_evidence_ids(s)
        gap = referenced - evidence_ids
        if gap:
            missing[s.inputs.scenario_id] = sorted(gap)
    if missing:
        raise AssertionError(f"scenarios reference evidence_ids missing from the corpus: {missing}")

    for e in b.evidence:
        expected_hash = hashlib.sha256(e.content.encode("utf-8")).hexdigest()
        assert e.content_sha256 == expected_hash, f"content_sha256 mismatch for {e.evidence_id}"


def write_jsonl(path: Path, models: list) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for model in models:
            fh.write(json.dumps(model.model_dump(mode="json"), ensure_ascii=False))
            fh.write("\n")


def main() -> None:
    b = build()
    validate(b)
    write_jsonl(EVIDENCE_PATH, b.evidence)
    write_jsonl(SCENARIOS_PATH, b.scenarios)
    print(f"Wrote {len(b.evidence)} evidence records to {EVIDENCE_PATH}")
    print(f"Wrote {len(b.scenarios)} scenarios to {SCENARIOS_PATH}")


if __name__ == "__main__":
    main()
