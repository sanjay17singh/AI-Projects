<a id="top"></a>

# Golden Dataset — 60 Test Case Specifications

This document specifies every scenario in the Market Research Agent's 60-scenario Golden Dataset (`gold-v1`), generated from `eval/datasets/golden_scenarios.jsonl` and `eval/datasets/frozen_evidence.jsonl`. These are the source of truth for regression evaluation — see `eval/README.md` for how to run them.

## Scenario families

| # | Family | Scenarios | Count | Primary purpose |
|---|---|---|---|---|
| 01 | [PASS Cases (MR-001 – MR-015)](#family-01) | MR-001 – MR-015 | 15 | Clean, unambiguous scenarios with a single well-supported answer. |
| 02 | [Retrieval-Quality Cases (MR-016 – MR-025)](#family-02) | MR-016 – MR-025 | 10 | Irrelevant/stale/low-authority evidence mixed in on purpose to test retrieval quality. |
| 03 | [Red-Flag Cases (MR-026 – MR-033)](#family-03) | MR-026 – MR-033 | 8 | One material negative development planted per scenario; checks red-flag surfacing. |
| 04 | [Missing-Information / Abstention Cases (MR-034 – MR-040)](#family-04) | MR-034 – MR-040 | 7 | No reliable evidence exists; checks correct abstention over hallucination. |
| 05 | [Conflicting-Evidence Cases (MR-041 – MR-048)](#family-05) | MR-041 – MR-048 | 8 | Two evidence sources disagree; checks preservation + justified resolution. |
| 06 | [Ground-Truth Coverage Cases (MR-049 – MR-053)](#family-06) | MR-049 – MR-053 | 5 | Multiple gold facts per competitor; checks ground-truth coverage. |
| 07 | [Cost-Projection Cases (MR-054 – MR-055)](#family-07) | MR-054 – MR-055 | 2 | Checks projected-vs-actual cost accuracy against a plausible cost band. |
| 08 | [Temporal / Freshness Cases (MR-056 – MR-058)](#family-08) | MR-056 – MR-058 | 3 | Old vs. new evidence values; checks current-value resolution + freshness. |
| 09 | [Resilience / Latency Cases (MR-059 – MR-060)](#family-09) | MR-059 – MR-060 | 2 | Simulated branch failure / latency; checks partial-failure handling and p95 latency. |

**Total: 60 scenarios.**

## Regenerating this document

This document is rendered directly from `eval/datasets/golden_scenarios.jsonl` and `eval/datasets/frozen_evidence.jsonl` — it is not hand-maintained. If you add or edit a scenario in `eval/datasets/generate_golden_dataset.py`, re-run the generator (`uv run python -m eval.datasets.generate_golden_dataset`) and then re-render this document from the updated JSONL files so it stays in sync. See `eval/README.md`'s "Adding a new Golden scenario" section for the full workflow.

---

<a id="family-01"></a>

# PASS Cases (MR-001 – MR-015)

[↑ Back to top](#top)

Clean, unambiguous scenarios with a single well-supported answer. These establish the floor: if the agent can't nail these, nothing else matters. Primary metrics are faithfulness and ground-truth coverage.

**15 scenarios in this family: MR-001, MR-002, MR-003, MR-004, MR-005, MR-006, MR-007, MR-008, MR-009, MR-010, MR-011, MR-012, MR-013, MR-014, MR-015**

---

## MR-001 — What does Northwind Analytics charge for its product?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Northwind Analytics |
| **Research category** | `pricing` |
| **top_k** | 5 |
| **Case type** | PASS |
| **Difficulty** | easy |
| **Primary metric** | Evidence Faithfulness |
| **Gold version** | gold-v1 |

### Expected answer
- Northwind Analytics charges $79 per seat per month, billed monthly.

### Gold facts

**pricing**
- `MR-001-F1` — Northwind Analytics charges $79/seat/month.
  - **Evidence:**
    - `EV-000001` — *official*, "Northwind Analytics -- Pricing" (2026-04-02) — https://northwindanalytics.io/pricing

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000001` — *official*, "Northwind Analytics -- Pricing" (2026-04-02) — https://northwindanalytics.io/pricing

---

## MR-002 — What pricing tiers does Vantage Loop offer?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Vantage Loop |
| **Research category** | `pricing` |
| **top_k** | 5 |
| **Case type** | PASS |
| **Difficulty** | easy |
| **Primary metric** | Evidence Faithfulness |
| **Gold version** | gold-v1 |

### Expected answer
- Vantage Loop has three tiers: Starter $29/mo, Growth $99/mo, Scale $249/mo.

### Gold facts

**pricing**
- `MR-002-F1` — Vantage Loop offers Starter ($29/mo), Growth ($99/mo), and Scale ($249/mo) tiers.
  - **Evidence:**
    - `EV-000002` — *official*, "Vantage Loop -- Plans & Pricing" (2026-03-15) — https://vantageloop.com/plans

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000002` — *official*, "Vantage Loop -- Plans & Pricing" (2026-03-15) — https://vantageloop.com/plans

---

## MR-003 — How does Cobalt Meridian's monthly pricing compare to its annual pricing?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Cobalt Meridian |
| **Research category** | `pricing` |
| **top_k** | 5 |
| **Case type** | PASS |
| **Difficulty** | easy |
| **Primary metric** | Evidence Faithfulness |
| **Gold version** | gold-v1 |

### Expected answer
- Cobalt Meridian charges $120/month or $1,080/year (a 25% annual discount).

### Gold facts

**pricing**
- `MR-003-F1` — Cobalt Meridian: $120/month, or $1,080/year (25% discount).
  - **Evidence:**
    - `EV-000003` — *official*, "Cobalt Meridian -- Pricing" (2026-02-20) — https://cobaltmeridian.com/pricing

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000003` — *official*, "Cobalt Meridian -- Pricing" (2026-02-20) — https://cobaltmeridian.com/pricing

---

## MR-004 — Does Fernbridge Data support real-time data sync with CRMs?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Fernbridge Data |
| **Research category** | `core_features` |
| **top_k** | 5 |
| **Case type** | PASS |
| **Difficulty** | easy |
| **Primary metric** | Evidence Faithfulness |
| **Gold version** | gold-v1 |

### Expected answer
- Fernbridge Data supports real-time bidirectional sync with Salesforce, HubSpot, and Snowflake.

### Gold facts

**core_features**
- `MR-004-F1` — Fernbridge Data offers real-time bidirectional CRM sync (<60s propagation).
  - **Evidence:**
    - `EV-000004` — *documentation*, "Fernbridge Data Documentation -- Real-Time Sync" (2026-01-10) — https://docs.fernbridgedata.com/features/real-time-sync

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000004` — *documentation*, "Fernbridge Data Documentation -- Real-Time Sync" (2026-01-10) — https://docs.fernbridgedata.com/features/real-time-sync

---

## MR-005 — Who is Solace Metrics' target customer segment?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Solace Metrics |
| **Research category** | `target_customers` |
| **top_k** | 5 |
| **Case type** | PASS |
| **Difficulty** | easy |
| **Primary metric** | Evidence Faithfulness |
| **Gold version** | gold-v1 |

### Expected answer
- Solace Metrics targets mid-market B2B SaaS companies (50-500 employees) without a dedicated data team.

### Gold facts

**target_customers**
- `MR-005-F1` — Solace Metrics targets mid-market B2B SaaS companies (50-500 employees).
  - **Evidence:**
    - `EV-000005` — *official*, "Solace Metrics -- Who We Serve" (2026-03-01) — https://solacemetrics.com/customers

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000005` — *official*, "Solace Metrics -- Who We Serve" (2026-03-01) — https://solacemetrics.com/customers

---

## MR-006 — How does Anchorpoint AI position itself in the market?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Anchorpoint AI |
| **Research category** | `positioning` |
| **top_k** | 5 |
| **Case type** | PASS |
| **Difficulty** | easy |
| **Primary metric** | Evidence Faithfulness |
| **Gold version** | gold-v1 |

### Expected answer
- Anchorpoint AI positions itself as the accuracy-first alternative, trading speed for verified answers.

### Gold facts

**positioning**
- `MR-006-F1` — Anchorpoint AI positions as 'accuracy-first', trading latency for citation-backed answers.
  - **Evidence:**
    - `EV-000006` — *official*, "Anchorpoint AI -- Our Approach" (2026-04-18) — https://anchorpoint.ai/about

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000006` — *official*, "Anchorpoint AI -- Our Approach" (2026-04-18) — https://anchorpoint.ai/about

---

## MR-007 — What is a verified differentiator for Lumen Cascade versus its competitors?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Lumen Cascade |
| **Research category** | `differentiators` |
| **top_k** | 5 |
| **Case type** | PASS |
| **Difficulty** | medium |
| **Primary metric** | Evidence Faithfulness |
| **Gold version** | gold-v1 |

### Expected answer
- Lumen Cascade's offline-first mode is a differentiator not offered by its closest competitors.

### Gold facts

**differentiators**
- `MR-007-F1` — Lumen Cascade differentiates with an offline-first mode absent from close competitors.
  - **Evidence:**
    - `EV-000007` — *reputable_news*, "TechNewsDaily -- Lumen Cascade Ships Offline-First Mode" (2026-05-02) — https://technewsdaily.example.com/lumen-cascade-offline-mode

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000007` — *reputable_news*, "TechNewsDaily -- Lumen Cascade Ships Offline-First Mode" (2026-05-02) — https://technewsdaily.example.com/lumen-cascade-offline-mode

---

## MR-008 — What did Driftwood Systems recently announce?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Driftwood Systems |
| **Research category** | `announcements` |
| **top_k** | 5 |
| **Case type** | PASS |
| **Difficulty** | easy |
| **Primary metric** | Evidence Faithfulness |
| **Gold version** | gold-v1 |

### Expected answer
- Driftwood Systems announced general availability of a no-code Workflow Builder.

### Gold facts

**announcements**
- `MR-008-F1` — Driftwood Systems announced GA of its no-code Workflow Builder.
  - **Evidence:**
    - `EV-000008` — *official*, "Driftwood Systems -- Introducing Workflow Builder" (2026-05-20) — https://driftwoodsystems.com/blog/introducing-workflow-builder

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000008` — *official*, "Driftwood Systems -- Introducing Workflow Builder" (2026-05-20) — https://driftwoodsystems.com/blog/introducing-workflow-builder

---

## MR-009 — What recent news is there about Harborlight Cloud?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Harborlight Cloud |
| **Research category** | `recent_news` |
| **top_k** | 5 |
| **Case type** | PASS |
| **Difficulty** | easy |
| **Primary metric** | Evidence Faithfulness |
| **Gold version** | gold-v1 |

### Expected answer
- Harborlight Cloud raised a $40M Series B to fund European expansion and engineering growth.

### Gold facts

**recent_news**
- `MR-009-F1` — Harborlight Cloud raised a $40M Series B (2026-05).
  - **Evidence:**
    - `EV-000009` — *reputable_news*, "CloudWire -- Harborlight Cloud Raises $40M Series B" (2026-05-28) — https://cloudwire.example.com/harborlight-series-b

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000009` — *reputable_news*, "CloudWire -- Harborlight Cloud Raises $40M Series B" (2026-05-28) — https://cloudwire.example.com/harborlight-series-b

---

## MR-010 — Does Northwind Analytics offer a free trial?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Northwind Analytics |
| **Research category** | `free_trial` |
| **top_k** | 5 |
| **Case type** | PASS |
| **Difficulty** | easy |
| **Primary metric** | Evidence Faithfulness |
| **Gold version** | gold-v1 |

### Expected answer
- Northwind Analytics offers a 14-day free trial with no credit card required.

### Gold facts

**free_trial**
- `MR-010-F1` — Northwind Analytics offers a 14-day free trial, no card required.
  - **Evidence:**
    - `EV-000010` — *official*, "Northwind Analytics -- Start Your Free Trial" (2026-04-05) — https://northwindanalytics.io/trial

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000010` — *official*, "Northwind Analytics -- Start Your Free Trial" (2026-04-05) — https://northwindanalytics.io/trial

---

## MR-011 — What do customer reviews say about Vantage Loop?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Vantage Loop |
| **Research category** | `customer_reviews` |
| **top_k** | 5 |
| **Case type** | PASS |
| **Difficulty** | easy |
| **Primary metric** | Evidence Faithfulness |
| **Gold version** | gold-v1 |

### Expected answer
- A verified reviewer rated Vantage Loop 4.5/5, citing fast onboarding but a weaker mobile app.

### Gold facts

**customer_reviews**
- `MR-011-F1` — Vantage Loop rated 4.5/5 by a verified reviewer; mobile app lags desktop.
  - **Evidence:**
    - `EV-000011` — *review*, "PeerReviews -- Vantage Loop Review" (2026-03-22) — https://peerreviews.example.com/vantage-loop/review-8821

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000011` — *review*, "PeerReviews -- Vantage Loop Review" (2026-03-22) — https://peerreviews.example.com/vantage-loop/review-8821

---

## MR-012 — Which notable customers does Cobalt Meridian have?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Cobalt Meridian |
| **Research category** | `notable_customers` |
| **top_k** | 5 |
| **Case type** | PASS |
| **Difficulty** | easy |
| **Primary metric** | Evidence Faithfulness |
| **Gold version** | gold-v1 |

### Expected answer
- Globex Retail Group is a named Cobalt Meridian customer, per an official case study.

### Gold facts

**notable_customers**
- `MR-012-F1` — Globex Retail Group is a named Cobalt Meridian customer.
  - **Evidence:**
    - `EV-000012` — *official*, "Cobalt Meridian -- Customer Story: Globex Retail Group" (2026-02-14) — https://cobaltmeridian.com/customers/case-study-globex

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000012` — *official*, "Cobalt Meridian -- Customer Story: Globex Retail Group" (2026-02-14) — https://cobaltmeridian.com/customers/case-study-globex

---

## MR-013 — What does Fernbridge Data do, in its own words?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Fernbridge Data |
| **Research category** | `company_description` |
| **top_k** | 5 |
| **Case type** | PASS |
| **Difficulty** | easy |
| **Primary metric** | Evidence Faithfulness |
| **Gold version** | gold-v1 |

### Expected answer
- Fernbridge Data unifies customer data from CRMs, billing, and support tools into one queryable layer.

### Gold facts

**company_description**
- `MR-013-F1` — Fernbridge Data unifies CRM/billing/support data into one queryable layer.
  - **Evidence:**
    - `EV-000013` — *official*, "Fernbridge Data -- About Us" (2026-01-05) — https://fernbridgedata.com/about

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000013` — *official*, "Fernbridge Data -- About Us" (2026-01-05) — https://fernbridgedata.com/about

---

## MR-014 — Is Solace Metrics' revenue forecasting feature corroborated by independent sources?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Solace Metrics |
| **Research category** | `core_features` |
| **top_k** | 5 |
| **Case type** | PASS |
| **Difficulty** | medium |
| **Primary metric** | Evidence Faithfulness |
| **Gold version** | gold-v1 |

### Expected answer
- Solace Metrics' revenue forecasting with confidence intervals is corroborated by an official source, independent press, and a user review.

### Gold facts

**core_features**
- `MR-014-F1` — Solace Metrics offers revenue forecasting with confidence intervals, confirmed by 3 independent sources.
  - **Evidence:**
    - `EV-000014` — *official*, "Solace Metrics -- Forecasting" (2026-02-01) — https://solacemetrics.com/features/forecasting
    - `EV-000015` — *reputable_news*, "SaaSToday -- Hands-on With Solace Metrics Forecasting" (2026-02-10) — https://saastoday.example.com/solace-metrics-forecasting-review
    - `EV-000016` — *review*, "PeerReviews -- Solace Metrics Review" (2026-02-18) — https://peerreviews.example.com/solace-metrics/review-4410

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000014` — *official*, "Solace Metrics -- Forecasting" (2026-02-01) — https://solacemetrics.com/features/forecasting
  - `EV-000015` — *reputable_news*, "SaaSToday -- Hands-on With Solace Metrics Forecasting" (2026-02-10) — https://saastoday.example.com/solace-metrics-forecasting-review
  - `EV-000016` — *review*, "PeerReviews -- Solace Metrics Review" (2026-02-18) — https://peerreviews.example.com/solace-metrics/review-4410

---

## MR-015 — How do Northwind Analytics and Vantage Loop compare on pricing this quarter?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Northwind Analytics, Vantage Loop |
| **Research category** | `pricing` |
| **top_k** | 5 |
| **Case type** | PASS |
| **Difficulty** | medium |
| **Primary metric** | Ground-Truth Coverage |
| **Gold version** | gold-v1 |

### Expected answer
- Northwind Analytics charges $79/seat/month.
- Vantage Loop's Growth tier is $99/month for up to 20 users.

### Gold facts

**pricing**
- `MR-015-F1` — Northwind Analytics: $79/seat/month.
  - **Evidence:**
    - `EV-000017` — *official*, "Northwind Analytics -- 2026 Pricing" (2026-05-01) — https://northwindanalytics.io/pricing-2026
- `MR-015-F2` — Vantage Loop Growth tier: $99/month, 20 users.
  - **Evidence:**
    - `EV-000018` — *official*, "Vantage Loop -- 2026 Plans" (2026-05-03) — https://vantageloop.com/plans-2026

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000017` — *official*, "Northwind Analytics -- 2026 Pricing" (2026-05-01) — https://northwindanalytics.io/pricing-2026
  - `EV-000018` — *official*, "Vantage Loop -- 2026 Plans" (2026-05-03) — https://vantageloop.com/plans-2026

---

<a id="family-02"></a>

# Retrieval-Quality Cases (MR-016 – MR-025)

[↑ Back to top](#top)

The Frozen Evidence Corpus for each of these scenarios deliberately mixes irrelevant, stale, or low-authority evidence in with the correct evidence, so retrieval quality (not just extraction quality) is under test. Primary metrics are Precision@3/Precision@5 and Recall@5, computed by exact evidence_id matching against `relevant_evidence_ids` — no LLM judgment involved.

**10 scenarios in this family: MR-016, MR-017, MR-018, MR-019, MR-020, MR-021, MR-022, MR-023, MR-024, MR-025**

---

## MR-016 — What does Anchorpoint AI charge for its Pro plan?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Anchorpoint AI |
| **Research category** | `pricing` |
| **top_k** | 5 |
| **Case type** | RETRIEVAL |
| **Difficulty** | medium |
| **Primary metric** | retrieval_precision_at_5 |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000019` — *official*, "Anchorpoint AI -- Pricing" (2026-04-10) — https://anchorpoint.ai/pricing

### Distractor evidence in the corpus (not relevant, but retrievable)
- **Distractors:**
  - `EV-000006` — *official*, "Anchorpoint AI -- Our Approach" (2026-04-18) — https://anchorpoint.ai/about
  - `EV-000020` — *blog*, "5 AI Tools Worth Trying This Year" (2025-08-01) — https://randomtechblog.example.com/5-ai-tools-worth-trying
  - `EV-000021` — *blog*, "My Morning Routine as a Remote Founder" (2025-06-15) — https://randomtechblog.example.com/my-morning-routine
  - `EV-000022` — *community*, "Forum: Anchorpoint vs alternatives?" (2025-09-20) — https://forum.example.com/thread/anchorpoint-vs-alternatives
  - `EV-000045` — *low_authority*, "Aggregator Summary: Anchorpoint AI" (2025-05-01) — https://aggregator.example.com/anchorpoint-summary
  - `EV-000046` — *official*, "Anchorpoint AI -- About" (2026-01-20) — https://anchorpoint.ai/about
  - `EV-000056` — *low_authority*, "Unverified: Companies That Might Use Anchorpoint AI" (2025-03-01) — https://spamdirectory.example.com/anchorpoint-clients-maybe
  - `EV-000069` — *official*, "Anchorpoint AI -- About (company history)" (2026-01-01) — https://anchorpoint.ai/about
  - `EV-000070` — *blog*, "TechArchive -- Anchorpoint AI's Early Days" (2025-04-01) — https://techarchive.example.com/anchorpoint-early-days
  - `EV-000129` — *blog*, "TechArchive -- Anchorpoint AI in 2024" (2024-05-01) — https://techarchive.example.com/anchorpoint-2024-positioning
  - `EV-000130` — *official*, "Anchorpoint AI -- About (current)" (2026-01-20) — https://anchorpoint.ai/about

---

## MR-017 — What is Lumen Cascade's monthly pricing?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Lumen Cascade |
| **Research category** | `pricing` |
| **top_k** | 5 |
| **Case type** | RETRIEVAL |
| **Difficulty** | hard |
| **Primary metric** | retrieval_precision_at_5 |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000023` — *official*, "Lumen Cascade -- Pricing" (2026-03-30) — https://lumencascade.com/pricing

### Distractor evidence in the corpus (not relevant, but retrievable)
- **Distractors:**
  - `EV-000007` — *reputable_news*, "TechNewsDaily -- Lumen Cascade Ships Offline-First Mode" (2026-05-02) — https://technewsdaily.example.com/lumen-cascade-offline-mode
  - `EV-000054` — *reputable_news*, "CloudWire -- Lumen Cascade Acquired by Meridian Holdings" (2026-05-10) — https://cloudwire.example.com/lumen-cascade-acquired
  - `EV-000073` — *official*, "Lumen Cascade -- Features" (2026-02-10) — https://lumencascade.com/features
  - `EV-000074` — *review*, "PeerReviews -- Lumen Cascade Review" (2026-03-01) — https://peerreviews.example.com/lumen-cascade/review-5541

---

## MR-018 — What does Driftwood Systems' Pulse feature do?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Driftwood Systems |
| **Research category** | `core_features` |
| **top_k** | 5 |
| **Case type** | RETRIEVAL |
| **Difficulty** | hard |
| **Primary metric** | retrieval_precision_at_5 |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000026` — *documentation*, "Driftwood Systems -- Pulse Monitoring" (2026-02-25) — https://docs.driftwoodsystems.com/features/pulse

### Distractor evidence in the corpus (not relevant, but retrievable)
- **Distractors:**
  - `EV-000008` — *official*, "Driftwood Systems -- Introducing Workflow Builder" (2026-05-20) — https://driftwoodsystems.com/blog/introducing-workflow-builder
  - `EV-000050` — *reputable_news*, "CloudWire -- Driftwood Systems Cuts 18% of Staff" (2026-04-05) — https://cloudwire.example.com/driftwood-layoffs
  - `EV-000059` — *official*, "Driftwood Systems -- Pricing" (2026-05-15) — https://driftwoodsystems.com/pricing
  - `EV-000060` — *review*, "PeerReviews -- Driftwood Systems Review" (2026-01-20) — https://peerreviews.example.com/driftwood-systems/review-3301

---

## MR-019 — What is Harborlight Cloud's current monthly price?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Harborlight Cloud |
| **Research category** | `pricing` |
| **top_k** | 5 |
| **Case type** | RETRIEVAL |
| **Difficulty** | hard |
| **Primary metric** | retrieval_precision_at_5 |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000030` — *official*, "Harborlight Cloud -- Current Pricing" (2026-01-15) — https://harborlightcloud.com/pricing

### Distractor evidence in the corpus (not relevant, but retrievable)
- **Distractors:**
  - `EV-000009` — *reputable_news*, "CloudWire -- Harborlight Cloud Raises $40M Series B" (2026-05-28) — https://cloudwire.example.com/harborlight-series-b
  - `EV-000029` — *low_authority*, "Archived: Harborlight Cloud Pricing (2024 snapshot)" (2024-06-01) — https://archived-pricing.example.com/harborlight-2024
  - `EV-000047` — *reputable_news*, "CloudWire -- Harborlight Cloud Raises Prices 50%" (2026-01-10) — https://cloudwire.example.com/harborlight-price-hike
  - `EV-000055` — *low_authority*, "Random Forum: Anyone used Harborlight Cloud?" (2025-01-01) — https://randomforum.example.com/thread/harborlight-anyone-used-it
  - `EV-000065` — *official*, "Harborlight Cloud -- About" (2026-02-01) — https://harborlightcloud.com/about
  - `EV-000066` — *reputable_news*, "CloudWire -- Company Profile: Harborlight Cloud" (2025-10-01) — https://cloudwire.example.com/harborlight-profile

---

## MR-020 — What differentiates Cobalt Meridian from other analytics vendors?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Cobalt Meridian |
| **Research category** | `differentiators` |
| **top_k** | 5 |
| **Case type** | RETRIEVAL |
| **Difficulty** | medium |
| **Primary metric** | retrieval_precision_at_5 |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000031` — *official*, "Cobalt Meridian -- Why Choose Us" (2026-03-05) — https://cobaltmeridian.com/why-us

### Distractor evidence in the corpus (not relevant, but retrievable)
- **Distractors:**
  - `EV-000003` — *official*, "Cobalt Meridian -- Pricing" (2026-02-20) — https://cobaltmeridian.com/pricing
  - `EV-000012` — *official*, "Cobalt Meridian -- Customer Story: Globex Retail Group" (2026-02-14) — https://cobaltmeridian.com/customers/case-study-globex
  - `EV-000052` — *review*, "PeerReviews -- Cobalt Meridian Rating Trend" (2026-04-12) — https://peerreviews.example.com/cobalt-meridian/aggregate-trend
  - `EV-000071` — *official*, "Cobalt Meridian -- About" (2025-12-01) — https://cobaltmeridian.com/about
  - `EV-000072` — *reputable_news*, "CloudWire -- Cobalt Meridian Acquired by Vantis Group" (2026-04-20) — https://cloudwire.example.com/cobalt-meridian-acquired-by-vantis
  - `EV-000095` — *official*, "Cobalt Meridian -- Pricing" (2026-03-01) — https://cobaltmeridian.example.com/pricing
  - `EV-000096` — *documentation*, "Cobalt Meridian Documentation -- Core Features" (2026-02-15) — https://docs.cobaltmeridian.example.com/features
  - `EV-000097` — *official*, "Cobalt Meridian -- Who It's For" (2026-01-20) — https://cobaltmeridian.example.com/customers
  - `EV-000098` — *official*, "Cobalt Meridian -- Positioning" (2026-02-01) — https://cobaltmeridian.example.com/about
  - `EV-000099` — *reputable_news*, "SaaSToday -- Cobalt Meridian Review" (2026-03-10) — https://saastoday.example.com/cobaltmeridian-review
  - `EV-000100` — *official*, "Cobalt Meridian -- New Integration Announced" (2026-04-01) — https://cobaltmeridian.example.com/blog/new-integration
  - `EV-000101` — *reputable_news*, "CloudWire -- Cobalt Meridian Hits Growth Milestone" (2026-04-15) — https://cloudwire.example.com/cobaltmeridian-milestone
  - `EV-000102` — *official*, "Cobalt Meridian -- Free Trial" (2026-03-20) — https://cobaltmeridian.example.com/trial
  - `EV-000103` — *review*, "PeerReviews -- Cobalt Meridian Summary" (2026-03-25) — https://peerreviews.example.com/cobaltmeridian/summary
  - `EV-000104` — *official*, "Cobalt Meridian -- Case Studies" (2026-02-20) — https://cobaltmeridian.example.com/customers/case-studies

---

## MR-021 — What do genuine customer reviews say about Solace Metrics?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Solace Metrics |
| **Research category** | `customer_reviews` |
| **top_k** | 5 |
| **Case type** | RETRIEVAL |
| **Difficulty** | hard |
| **Primary metric** | retrieval_precision_at_5 |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000034` — *review*, "PeerReviews -- Solace Metrics Verified Review" (2026-04-01) — https://peerreviews.example.com/solace-metrics/review-9012

### Distractor evidence in the corpus (not relevant, but retrievable)
- **Distractors:**
  - `EV-000005` — *official*, "Solace Metrics -- Who We Serve" (2026-03-01) — https://solacemetrics.com/customers
  - `EV-000014` — *official*, "Solace Metrics -- Forecasting" (2026-02-01) — https://solacemetrics.com/features/forecasting
  - `EV-000015` — *reputable_news*, "SaaSToday -- Hands-on With Solace Metrics Forecasting" (2026-02-10) — https://saastoday.example.com/solace-metrics-forecasting-review
  - `EV-000016` — *review*, "PeerReviews -- Solace Metrics Review" (2026-02-18) — https://peerreviews.example.com/solace-metrics/review-4410
  - `EV-000035` — *review*, "Review of CompetitorX (mentions Solace Metrics)" (2025-12-01) — https://peerreviews.example.com/other-vendor/review-comparing-solace
  - `EV-000036` — *low_authority*, "Is Solace Metrics a Scam? (clickbait)" (2025-11-20) — https://spamreviews.example.com/solace-metrics-scam-warning
  - `EV-000051` — *regulatory*, "RegulatorWatch -- Data Protection Authority Opens Inquiry Into Solace Metrics" (2026-03-25) — https://regulatorwatch.example.com/solace-metrics-inquiry
  - `EV-000067` — *official*, "Solace Metrics -- About" (2026-01-15) — https://solacemetrics.com/about
  - `EV-000068` — *reputable_news*, "SaaSToday -- Solace Metrics Growth Profile" (2025-11-05) — https://saastoday.example.com/solace-metrics-growth-profile
  - `EV-000115` — *official*, "Solace Metrics -- Pricing" (2026-03-01) — https://solacemetrics.example.com/pricing
  - `EV-000116` — *documentation*, "Solace Metrics Documentation -- Core Features" (2026-02-15) — https://docs.solacemetrics.example.com/features
  - `EV-000117` — *official*, "Solace Metrics -- Who It's For" (2026-01-20) — https://solacemetrics.example.com/customers
  - `EV-000118` — *official*, "Solace Metrics -- Positioning" (2026-02-01) — https://solacemetrics.example.com/about
  - `EV-000119` — *reputable_news*, "SaaSToday -- Solace Metrics Review" (2026-03-10) — https://saastoday.example.com/solacemetrics-review
  - `EV-000120` — *official*, "Solace Metrics -- New Integration Announced" (2026-04-01) — https://solacemetrics.example.com/blog/new-integration
  - `EV-000121` — *reputable_news*, "CloudWire -- Solace Metrics Hits Growth Milestone" (2026-04-15) — https://cloudwire.example.com/solacemetrics-milestone
  - `EV-000122` — *official*, "Solace Metrics -- Free Trial" (2026-03-20) — https://solacemetrics.example.com/trial
  - `EV-000123` — *review*, "PeerReviews -- Solace Metrics Summary" (2026-03-25) — https://peerreviews.example.com/solacemetrics/summary
  - `EV-000124` — *official*, "Solace Metrics -- Case Studies" (2026-02-20) — https://solacemetrics.example.com/customers/case-studies

---

## MR-022 — What does Fernbridge Data's customer-facing pipeline feature actually do?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Fernbridge Data |
| **Research category** | `core_features` |
| **top_k** | 5 |
| **Case type** | RETRIEVAL |
| **Difficulty** | hard |
| **Primary metric** | retrieval_precision_at_5 |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000037` — *documentation*, "Fernbridge Data Documentation -- Pipelines" (2026-02-05) — https://docs.fernbridgedata.com/features/pipelines

### Distractor evidence in the corpus (not relevant, but retrievable)
- **Distractors:**
  - `EV-000004` — *documentation*, "Fernbridge Data Documentation -- Real-Time Sync" (2026-01-10) — https://docs.fernbridgedata.com/features/real-time-sync
  - `EV-000013` — *official*, "Fernbridge Data -- About Us" (2026-01-05) — https://fernbridgedata.com/about
  - `EV-000038` — *low_authority*, "Fernbridge Data is hiring: Senior Pipeline Engineer" (2026-04-20) — https://jobs.example.com/fernbridge-data-senior-pipeline-engineer
  - `EV-000039` — *low_authority*, "Fernbridge Data is hiring: Platform Engineer" (2026-04-22) — https://jobs.example.com/fernbridge-data-platform-engineer
  - `EV-000053` — *documentation*, "Fernbridge Data Changelog -- April 2026" (2026-04-30) — https://docs.fernbridgedata.com/changelog/2026-04
  - `EV-000061` — *official*, "Fernbridge Data -- Free Trial" (2026-04-01) — https://fernbridgedata.com/trial
  - `EV-000062` — *partner*, "Fernbridge Reseller FAQ" (2025-08-01) — https://fernbridgereseller.example.com/faq
  - `EV-000105` — *official*, "Fernbridge Data -- Pricing" (2026-03-01) — https://fernbridgedata.example.com/pricing
  - `EV-000106` — *documentation*, "Fernbridge Data Documentation -- Core Features" (2026-02-15) — https://docs.fernbridgedata.example.com/features
  - `EV-000107` — *official*, "Fernbridge Data -- Who It's For" (2026-01-20) — https://fernbridgedata.example.com/customers
  - `EV-000108` — *official*, "Fernbridge Data -- Positioning" (2026-02-01) — https://fernbridgedata.example.com/about
  - `EV-000109` — *reputable_news*, "SaaSToday -- Fernbridge Data Review" (2026-03-10) — https://saastoday.example.com/fernbridgedata-review
  - `EV-000110` — *official*, "Fernbridge Data -- New Integration Announced" (2026-04-01) — https://fernbridgedata.example.com/blog/new-integration
  - `EV-000111` — *reputable_news*, "CloudWire -- Fernbridge Data Hits Growth Milestone" (2026-04-15) — https://cloudwire.example.com/fernbridgedata-milestone
  - `EV-000112` — *official*, "Fernbridge Data -- Free Trial" (2026-03-20) — https://fernbridgedata.example.com/trial
  - `EV-000113` — *review*, "PeerReviews -- Fernbridge Data Summary" (2026-03-25) — https://peerreviews.example.com/fernbridgedata/summary
  - `EV-000114` — *official*, "Fernbridge Data -- Case Studies" (2026-02-20) — https://fernbridgedata.example.com/customers/case-studies

---

## MR-023 — What is Northwind Analytics' official API rate limit?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Northwind Analytics |
| **Research category** | `core_features` |
| **top_k** | 5 |
| **Case type** | RETRIEVAL |
| **Difficulty** | medium |
| **Primary metric** | retrieval_precision_at_5 |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000040` — *documentation*, "Northwind Analytics Documentation -- API Rate Limits" (2026-03-10) — https://docs.northwindanalytics.io/api/rate-limits

### Distractor evidence in the corpus (not relevant, but retrievable)
- **Distractors:**
  - `EV-000001` — *official*, "Northwind Analytics -- Pricing" (2026-04-02) — https://northwindanalytics.io/pricing
  - `EV-000010` — *official*, "Northwind Analytics -- Start Your Free Trial" (2026-04-05) — https://northwindanalytics.io/trial
  - `EV-000017` — *official*, "Northwind Analytics -- 2026 Pricing" (2026-05-01) — https://northwindanalytics.io/pricing-2026
  - `EV-000049` — *reputable_news*, "SecurityWire -- Northwind Analytics Discloses Data Exposure" (2026-02-18) — https://securitywire.example.com/northwind-breach-disclosure
  - `EV-000058` — *documentation*, "Northwind Analytics Documentation -- Feature Overview" (2026-03-20) — https://docs.northwindanalytics.io/features/overview
  - `EV-000075` — *official*, "Northwind Analytics -- Pricing" (2026-03-01) — https://northwindanalytics.example.com/pricing
  - `EV-000076` — *documentation*, "Northwind Analytics Documentation -- Core Features" (2026-02-15) — https://docs.northwindanalytics.example.com/features
  - `EV-000077` — *official*, "Northwind Analytics -- Who It's For" (2026-01-20) — https://northwindanalytics.example.com/customers
  - `EV-000078` — *official*, "Northwind Analytics -- Positioning" (2026-02-01) — https://northwindanalytics.example.com/about
  - `EV-000079` — *reputable_news*, "SaaSToday -- Northwind Analytics Review" (2026-03-10) — https://saastoday.example.com/northwindanalytics-review
  - `EV-000080` — *official*, "Northwind Analytics -- New Integration Announced" (2026-04-01) — https://northwindanalytics.example.com/blog/new-integration
  - `EV-000081` — *reputable_news*, "CloudWire -- Northwind Analytics Hits Growth Milestone" (2026-04-15) — https://cloudwire.example.com/northwindanalytics-milestone
  - `EV-000082` — *official*, "Northwind Analytics -- Free Trial" (2026-03-20) — https://northwindanalytics.example.com/trial
  - `EV-000083` — *review*, "PeerReviews -- Northwind Analytics Summary" (2026-03-25) — https://peerreviews.example.com/northwindanalytics/summary
  - `EV-000084` — *official*, "Northwind Analytics -- Case Studies" (2026-02-20) — https://northwindanalytics.example.com/customers/case-studies
  - `EV-000125` — *official*, "Northwind Analytics -- Pricing (2025 archive)" (2025-06-01) — https://web.archive.example.com/northwindanalytics-2025
  - `EV-000126` — *official*, "Northwind Analytics -- Current Pricing" (2026-02-01) — https://northwindanalytics.io/pricing
  - `EV-000131` — *official*, "Northwind Analytics -- Pricing" (2026-05-01) — https://northwindanalytics.io/pricing

---

## MR-024 — Does Vantage Loop offer a free trial, and on what terms?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Vantage Loop |
| **Research category** | `free_trial` |
| **top_k** | 5 |
| **Case type** | RETRIEVAL |
| **Difficulty** | medium |
| **Primary metric** | retrieval_recall_at_5 |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000042` — *official*, "Vantage Loop -- Free Trial" (2026-04-15) — https://vantageloop.com/trial

### Distractor evidence in the corpus (not relevant, but retrievable)
- **Distractors:**
  - `EV-000002` — *official*, "Vantage Loop -- Plans & Pricing" (2026-03-15) — https://vantageloop.com/plans
  - `EV-000011` — *review*, "PeerReviews -- Vantage Loop Review" (2026-03-22) — https://peerreviews.example.com/vantage-loop/review-8821
  - `EV-000018` — *official*, "Vantage Loop -- 2026 Plans" (2026-05-03) — https://vantageloop.com/plans-2026
  - `EV-000043` — *blog*, "Vantage Loop -- Free Trial (mirrored)" (2026-04-16) — https://mirror1.example.com/vantage-loop-trial
  - `EV-000044` — *blog*, "Vantage Loop -- Free Trial (syndicated copy)" (2026-04-17) — https://mirror2.example.com/vantage-loop-trial-copy
  - `EV-000048` — *official*, "Vantage Loop -- Sunsetting the Legacy Reports Module" (2026-03-01) — https://vantageloop.com/blog/sunsetting-legacy-reports
  - `EV-000057` — *blog*, "Vantage Loop Launches (2022 archive)" (2022-06-01) — https://oldnews.example.com/vantage-loop-2022-launch
  - `EV-000063` — *documentation*, "Vantage Loop Documentation -- Legacy Export (archived version)" (2025-06-01) — https://docs.vantageloop.com/features/legacy-export
  - `EV-000064` — *documentation*, "Vantage Loop Changelog -- March 2026" (2026-03-01) — https://docs.vantageloop.com/changelog/2026-03
  - `EV-000085` — *official*, "Vantage Loop -- Pricing" (2026-03-01) — https://vantageloop.example.com/pricing
  - `EV-000086` — *documentation*, "Vantage Loop Documentation -- Core Features" (2026-02-15) — https://docs.vantageloop.example.com/features
  - `EV-000087` — *official*, "Vantage Loop -- Who It's For" (2026-01-20) — https://vantageloop.example.com/customers
  - `EV-000088` — *official*, "Vantage Loop -- Positioning" (2026-02-01) — https://vantageloop.example.com/about
  - `EV-000089` — *reputable_news*, "SaaSToday -- Vantage Loop Review" (2026-03-10) — https://saastoday.example.com/vantageloop-review
  - `EV-000090` — *official*, "Vantage Loop -- New Integration Announced" (2026-04-01) — https://vantageloop.example.com/blog/new-integration
  - `EV-000091` — *reputable_news*, "CloudWire -- Vantage Loop Hits Growth Milestone" (2026-04-15) — https://cloudwire.example.com/vantageloop-milestone
  - `EV-000092` — *official*, "Vantage Loop -- Free Trial" (2026-03-20) — https://vantageloop.example.com/trial
  - `EV-000093` — *review*, "PeerReviews -- Vantage Loop Summary" (2026-03-25) — https://peerreviews.example.com/vantageloop/summary
  - `EV-000094` — *official*, "Vantage Loop -- Case Studies" (2026-02-20) — https://vantageloop.example.com/customers/case-studies
  - `EV-000127` — *blog*, "Vantage Loop -- Features (cached 2025 copy)" (2025-09-01) — https://mirror-cache.example.com/vantage-loop-features-2025
  - `EV-000128` — *documentation*, "Vantage Loop Changelog -- January 2026" (2026-01-15) — https://docs.vantageloop.com/changelog/2026-01
  - `EV-000132` — *official*, "Vantage Loop -- Plans & Pricing" (2026-05-01) — https://vantageloop.com/plans

---

## MR-025 — How does Anchorpoint AI describe its own market positioning?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Anchorpoint AI |
| **Research category** | `positioning` |
| **top_k** | 5 |
| **Case type** | RETRIEVAL |
| **Difficulty** | hard |
| **Primary metric** | retrieval_precision_at_5 |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000046` — *official*, "Anchorpoint AI -- About" (2026-01-20) — https://anchorpoint.ai/about

### Distractor evidence in the corpus (not relevant, but retrievable)
- **Distractors:**
  - `EV-000006` — *official*, "Anchorpoint AI -- Our Approach" (2026-04-18) — https://anchorpoint.ai/about
  - `EV-000019` — *official*, "Anchorpoint AI -- Pricing" (2026-04-10) — https://anchorpoint.ai/pricing
  - `EV-000020` — *blog*, "5 AI Tools Worth Trying This Year" (2025-08-01) — https://randomtechblog.example.com/5-ai-tools-worth-trying
  - `EV-000021` — *blog*, "My Morning Routine as a Remote Founder" (2025-06-15) — https://randomtechblog.example.com/my-morning-routine
  - `EV-000022` — *community*, "Forum: Anchorpoint vs alternatives?" (2025-09-20) — https://forum.example.com/thread/anchorpoint-vs-alternatives
  - `EV-000045` — *low_authority*, "Aggregator Summary: Anchorpoint AI" (2025-05-01) — https://aggregator.example.com/anchorpoint-summary
  - `EV-000056` — *low_authority*, "Unverified: Companies That Might Use Anchorpoint AI" (2025-03-01) — https://spamdirectory.example.com/anchorpoint-clients-maybe
  - `EV-000069` — *official*, "Anchorpoint AI -- About (company history)" (2026-01-01) — https://anchorpoint.ai/about
  - `EV-000070` — *blog*, "TechArchive -- Anchorpoint AI's Early Days" (2025-04-01) — https://techarchive.example.com/anchorpoint-early-days
  - `EV-000129` — *blog*, "TechArchive -- Anchorpoint AI in 2024" (2024-05-01) — https://techarchive.example.com/anchorpoint-2024-positioning
  - `EV-000130` — *official*, "Anchorpoint AI -- About (current)" (2026-01-20) — https://anchorpoint.ai/about

---

<a id="family-03"></a>

# Red-Flag Cases (MR-026 – MR-033)

[↑ Back to top](#top)

Each scenario plants exactly one material negative development in the evidence corpus and checks whether the agent surfaces it as a `RedFlag` with the right severity. `is_critical` flags require 100% recall at release (a hard gate — see `eval/evaluators/release_gate.py`). Judged by `judges/red_flag_judge.py` (semantic matching, since wording won't match verbatim) and scored via `evaluators/red_flag_recall.py` / `red_flag_precision.py`.

**8 scenarios in this family: MR-026, MR-027, MR-028, MR-029, MR-030, MR-031, MR-032, MR-033**

---

## MR-026 — Has Harborlight Cloud made any significant pricing changes recently?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Harborlight Cloud |
| **Research category** | `pricing` |
| **top_k** | 5 |
| **Case type** | RED_FLAG |
| **Difficulty** | medium |
| **Primary metric** | Red-Flag Recall |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

### Gold red flags
- **RF-026-1** — `price_increase` (severity: **medium**)
  - Harborlight Cloud raised its standard plan price 50% ($59 to $89/month).
  - Expected agent response: _Flag the 50% price increase as a material red flag with the cited evidence, without inventing a reason beyond what the source states._
  - **Evidence:**
    - `EV-000047` — *reputable_news*, "CloudWire -- Harborlight Cloud Raises Prices 50%" (2026-01-10) — https://cloudwire.example.com/harborlight-price-hike

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000047` — *reputable_news*, "CloudWire -- Harborlight Cloud Raises Prices 50%" (2026-01-10) — https://cloudwire.example.com/harborlight-price-hike

---

## MR-027 — Is Vantage Loop discontinuing any product modules?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Vantage Loop |
| **Research category** | `announcements` |
| **top_k** | 5 |
| **Case type** | RED_FLAG |
| **Difficulty** | medium |
| **Primary metric** | critical_red_flag_recall |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

### Gold red flags
- **RF-027-1** — `product_discontinuation` (severity: **high**, CRITICAL)
  - Vantage Loop is discontinuing its Legacy Reports module with no replacement for the custom export format.
  - Expected agent response: _Flag the discontinuation as critical since affected customers have no migration path, citing the official announcement._
  - **Evidence:**
    - `EV-000048` — *official*, "Vantage Loop -- Sunsetting the Legacy Reports Module" (2026-03-01) — https://vantageloop.com/blog/sunsetting-legacy-reports

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000048` — *official*, "Vantage Loop -- Sunsetting the Legacy Reports Module" (2026-03-01) — https://vantageloop.com/blog/sunsetting-legacy-reports

---

## MR-028 — Has Northwind Analytics had any security incidents?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Northwind Analytics |
| **Research category** | `recent_news` |
| **top_k** | 5 |
| **Case type** | RED_FLAG |
| **Difficulty** | hard |
| **Primary metric** | critical_red_flag_recall |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

### Gold red flags
- **RF-028-1** — `security_incident` (severity: **critical**, CRITICAL)
  - Northwind Analytics disclosed a data exposure incident affecting customer dashboard metadata for ~11 days.
  - Expected agent response: _Flag the disclosed security incident as critical, citing the source, and note the company's stated scope (metadata only, no passwords/payment data) without overstating it._
  - **Evidence:**
    - `EV-000049` — *reputable_news*, "SecurityWire -- Northwind Analytics Discloses Data Exposure" (2026-02-18) — https://securitywire.example.com/northwind-breach-disclosure

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000049` — *reputable_news*, "SecurityWire -- Northwind Analytics Discloses Data Exposure" (2026-02-18) — https://securitywire.example.com/northwind-breach-disclosure

---

## MR-029 — Has Driftwood Systems undergone layoffs or restructuring recently?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Driftwood Systems |
| **Research category** | `recent_news` |
| **top_k** | 5 |
| **Case type** | RED_FLAG |
| **Difficulty** | medium |
| **Primary metric** | Red-Flag Recall |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

### Gold red flags
- **RF-029-1** — `layoffs` (severity: **medium**)
  - Driftwood Systems laid off about 18% of staff as part of a cash-runway-extending restructuring.
  - Expected agent response: _Flag the layoffs as a red flag with the cited scope, without speculating about product impact beyond what the source states._
  - **Evidence:**
    - `EV-000050` — *reputable_news*, "CloudWire -- Driftwood Systems Cuts 18% of Staff" (2026-04-05) — https://cloudwire.example.com/driftwood-layoffs

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000050` — *reputable_news*, "CloudWire -- Driftwood Systems Cuts 18% of Staff" (2026-04-05) — https://cloudwire.example.com/driftwood-layoffs

---

## MR-030 — Is Solace Metrics facing any regulatory or legal issues?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Solace Metrics |
| **Research category** | `recent_news` |
| **top_k** | 5 |
| **Case type** | RED_FLAG |
| **Difficulty** | hard |
| **Primary metric** | critical_red_flag_recall |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

### Gold red flags
- **RF-030-1** — `regulatory_inquiry` (severity: **high**, CRITICAL)
  - A data protection authority opened an unresolved inquiry into Solace Metrics' data retention practices.
  - Expected agent response: _Flag the open regulatory inquiry as critical given it is unresolved, citing the source and being explicit that no findings have been issued yet._
  - **Evidence:**
    - `EV-000051` — *regulatory*, "RegulatorWatch -- Data Protection Authority Opens Inquiry Into Solace Metrics" (2026-03-25) — https://regulatorwatch.example.com/solace-metrics-inquiry

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000051` — *regulatory*, "RegulatorWatch -- Data Protection Authority Opens Inquiry Into Solace Metrics" (2026-03-25) — https://regulatorwatch.example.com/solace-metrics-inquiry

---

## MR-031 — Are there signs of significant customer churn or complaints for Cobalt Meridian?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Cobalt Meridian |
| **Research category** | `customer_reviews` |
| **top_k** | 5 |
| **Case type** | RED_FLAG |
| **Difficulty** | medium |
| **Primary metric** | Red-Flag Recall |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

### Gold red flags
- **RF-031-1** — `customer_churn` (severity: **medium**)
  - Cobalt Meridian's review rating dropped from 4.3 to 3.1 over two quarters with reported cancellations tied to slow support.
  - Expected agent response: _Flag the rating decline and cited cancellations as a churn-related red flag, grounded in the review-trend evidence._
  - **Evidence:**
    - `EV-000052` — *review*, "PeerReviews -- Cobalt Meridian Rating Trend" (2026-04-12) — https://peerreviews.example.com/cobalt-meridian/aggregate-trend

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000052` — *review*, "PeerReviews -- Cobalt Meridian Rating Trend" (2026-04-12) — https://peerreviews.example.com/cobalt-meridian/aggregate-trend

---

## MR-032 — Has Fernbridge Data deprecated any features recently?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Fernbridge Data |
| **Research category** | `announcements` |
| **top_k** | 5 |
| **Case type** | RED_FLAG |
| **Difficulty** | easy |
| **Primary metric** | Red-Flag Recall |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

### Gold red flags
- **RF-032-1** — `feature_deprecation` (severity: **low**)
  - Fernbridge Data deprecated its legacy CSV export endpoint in favor of a new streaming export API.
  - Expected agent response: _Flag the deprecation as low severity with a migration path already offered, citing the changelog._
  - **Evidence:**
    - `EV-000053` — *documentation*, "Fernbridge Data Changelog -- April 2026" (2026-04-30) — https://docs.fernbridgedata.com/changelog/2026-04

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000053` — *documentation*, "Fernbridge Data Changelog -- April 2026" (2026-04-30) — https://docs.fernbridgedata.com/changelog/2026-04

---

## MR-033 — Has Lumen Cascade been acquired, and what does that mean for its product?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Lumen Cascade |
| **Research category** | `recent_news` |
| **top_k** | 5 |
| **Case type** | RED_FLAG |
| **Difficulty** | medium |
| **Primary metric** | Red-Flag Recall |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

### Gold red flags
- **RF-033-1** — `acquisition_uncertainty` (severity: **medium**)
  - Lumen Cascade was acquired by Meridian Holdings with no announced roadmap plans, creating product continuity uncertainty.
  - Expected agent response: _Flag the acquisition and note the roadmap uncertainty explicitly rather than assuming continuity or discontinuation._
  - **Evidence:**
    - `EV-000054` — *reputable_news*, "CloudWire -- Lumen Cascade Acquired by Meridian Holdings" (2026-05-10) — https://cloudwire.example.com/lumen-cascade-acquired

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000054` — *reputable_news*, "CloudWire -- Lumen Cascade Acquired by Meridian Holdings" (2026-05-10) — https://cloudwire.example.com/lumen-cascade-acquired

---

<a id="family-04"></a>

# Missing-Information / Abstention Cases (MR-034 – MR-040)

[↑ Back to top](#top)

Evidence for the requested fact does not exist in the corpus, or exists only as low-quality/irrelevant material. The correct agent behavior is to abstain explicitly (`Not publicly available` / `Unknown` / `Insufficient evidence`), never to fabricate. Judged by `judges/abstention_judge.py` on the 0-2 rubric, aggregated via `evaluators/abstention.py`.

**7 scenarios in this family: MR-034, MR-035, MR-036, MR-037, MR-038, MR-039, MR-040**

---

## MR-034 — What does Driftwood Systems charge for its Enterprise plan?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Driftwood Systems |
| **Research category** | `pricing` |
| **top_k** | 5 |
| **Case type** | MISSING_INFO |
| **Difficulty** | medium |
| **Primary metric** | unsupported_claim_rate |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

**Expected abstention:**
- Not publicly available
- Unknown

---

## MR-035 — Does Cobalt Meridian offer a free trial?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Cobalt Meridian |
| **Research category** | `free_trial` |
| **top_k** | 5 |
| **Case type** | MISSING_INFO |
| **Difficulty** | medium |
| **Primary metric** | unsupported_claim_rate |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

**Expected abstention:**
- Not publicly available
- No reliable evidence found

---

## MR-036 — What do reliable customer reviews say about Harborlight Cloud?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Harborlight Cloud |
| **Research category** | `customer_reviews` |
| **top_k** | 5 |
| **Case type** | MISSING_INFO |
| **Difficulty** | hard |
| **Primary metric** | unsupported_claim_rate |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

**Expected abstention:**
- Insufficient evidence
- No reliable evidence found

---

## MR-037 — Which notable customers does Anchorpoint AI have?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Anchorpoint AI |
| **Research category** | `notable_customers` |
| **top_k** | 5 |
| **Case type** | MISSING_INFO |
| **Difficulty** | hard |
| **Primary metric** | unsupported_claim_rate |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

**Expected abstention:**
- Insufficient evidence
- Unknown

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000056` — *low_authority*, "Unverified: Companies That Might Use Anchorpoint AI" (2025-03-01) — https://spamdirectory.example.com/anchorpoint-clients-maybe

---

## MR-038 — What recent news is there about Vantage Loop in the last quarter?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Vantage Loop |
| **Research category** | `recent_news` |
| **top_k** | 5 |
| **Case type** | MISSING_INFO |
| **Difficulty** | medium |
| **Primary metric** | unsupported_claim_rate |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

**Expected abstention:**
- No reliable evidence found
- Not publicly available

---

## MR-039 — Does Northwind Analytics support offline editing on mobile?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Northwind Analytics |
| **Research category** | `core_features` |
| **top_k** | 5 |
| **Case type** | MISSING_INFO |
| **Difficulty** | hard |
| **Primary metric** | unsupported_claim_rate |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

**Expected abstention:**
- Not publicly available
- Insufficient evidence

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000058` — *documentation*, "Northwind Analytics Documentation -- Feature Overview" (2026-03-20) — https://docs.northwindanalytics.io/features/overview

---

## MR-040 — What is Solace Metrics' current core feature set, per its website?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Solace Metrics |
| **Research category** | `core_features` |
| **top_k** | 5 |
| **Case type** | MISSING_INFO |
| **Difficulty** | medium |
| **Primary metric** | unsupported_claim_rate |
| **Gold version** | gold-v1 |

**Simulation parameters:** `{"source_unavailable": "solacemetrics.com"}`

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

**Expected abstention:**
- Not publicly available
- Unknown
- No reliable evidence found

---

<a id="family-05"></a>

# Conflicting-Evidence Cases (MR-041 – MR-048)

[↑ Back to top](#top)

Two pieces of evidence disagree on the same fact. The agent must preserve *both* values (never silently collapse to one) and, only when the evidence itself supports it, prefer one value with a stated reason — otherwise it must leave the conflict `unresolved` or `human_review_required`. Judged by `judges/conflict_judge.py` on the 0-4 rubric, aggregated via `evaluators/conflict_resolution.py`.

**8 scenarios in this family: MR-041, MR-042, MR-043, MR-044, MR-045, MR-046, MR-047, MR-048**

---

## MR-041 — What is Driftwood Systems' Growth plan price?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Driftwood Systems |
| **Research category** | `pricing` |
| **top_k** | 5 |
| **Case type** | CONFLICT |
| **Difficulty** | medium |
| **Primary metric** | Conflict-Resolution Correctness |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

### Gold conflicts
- **Field:** `pricing`
  - Value A: "$99/month" (official, 2026-05-15)
    - **Evidence A:**
      - `EV-000059` — *official*, "Driftwood Systems -- Pricing" (2026-05-15) — https://driftwoodsystems.com/pricing
  - Value B: "$129/month" (review, 2026-01-20)
    - **Evidence B:**
      - `EV-000060` — *review*, "PeerReviews -- Driftwood Systems Review" (2026-01-20) — https://peerreviews.example.com/driftwood-systems/review-3301
  - **Expected preferred value:** $99/month
  - **Expected resolution reason:** The official, more recently updated pricing page should be preferred over an older third-party review mentioning a stale price.

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000059` — *official*, "Driftwood Systems -- Pricing" (2026-05-15) — https://driftwoodsystems.com/pricing
  - `EV-000060` — *review*, "PeerReviews -- Driftwood Systems Review" (2026-01-20) — https://peerreviews.example.com/driftwood-systems/review-3301

---

## MR-042 — Does Fernbridge Data offer a free trial?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Fernbridge Data |
| **Research category** | `free_trial` |
| **top_k** | 5 |
| **Case type** | CONFLICT |
| **Difficulty** | medium |
| **Primary metric** | Conflict-Resolution Correctness |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

### Gold conflicts
- **Field:** `free_trial`
  - Value A: "Yes, 14-day free trial" (official, 2026-04-01)
    - **Evidence A:**
      - `EV-000061` — *official*, "Fernbridge Data -- Free Trial" (2026-04-01) — https://fernbridgedata.com/trial
  - Value B: "No, demo call only" (partner, 2025-08-01)
    - **Evidence B:**
      - `EV-000062` — *partner*, "Fernbridge Reseller FAQ" (2025-08-01) — https://fernbridgereseller.example.com/faq
  - **Expected preferred value:** Yes, 14-day free trial
  - **Expected resolution reason:** The official, more recent source should be preferred over a stale partner FAQ.

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000061` — *official*, "Fernbridge Data -- Free Trial" (2026-04-01) — https://fernbridgedata.com/trial
  - `EV-000062` — *partner*, "Fernbridge Reseller FAQ" (2025-08-01) — https://fernbridgereseller.example.com/faq

---

## MR-043 — Is Vantage Loop's Legacy Export feature still available?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Vantage Loop |
| **Research category** | `core_features` |
| **top_k** | 5 |
| **Case type** | CONFLICT |
| **Difficulty** | medium |
| **Primary metric** | Conflict-Resolution Correctness |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

### Gold conflicts
- **Field:** `core_features`
  - Value A: "Legacy Export available" (documentation, 2025-06-01)
    - **Evidence A:**
      - `EV-000063` — *documentation*, "Vantage Loop Documentation -- Legacy Export (archived version)" (2025-06-01) — https://docs.vantageloop.com/features/legacy-export
  - Value B: "Legacy Export removed/deprecated" (documentation, 2026-03-01)
    - **Evidence B:**
      - `EV-000064` — *documentation*, "Vantage Loop Changelog -- March 2026" (2026-03-01) — https://docs.vantageloop.com/changelog/2026-03
  - **Expected preferred value:** Legacy Export removed/deprecated
  - **Expected resolution reason:** The more recent changelog supersedes the older archived documentation snapshot.

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000063` — *documentation*, "Vantage Loop Documentation -- Legacy Export (archived version)" (2025-06-01) — https://docs.vantageloop.com/features/legacy-export
  - `EV-000064` — *documentation*, "Vantage Loop Changelog -- March 2026" (2026-03-01) — https://docs.vantageloop.com/changelog/2026-03

---

## MR-044 — How many employees does Harborlight Cloud have?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Harborlight Cloud |
| **Research category** | `company_description` |
| **top_k** | 5 |
| **Case type** | CONFLICT |
| **Difficulty** | hard |
| **Primary metric** | Conflict-Resolution Correctness |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

### Gold conflicts
- **Field:** `company_description`
  - Value A: "150+ employees" (official, 2026-02-01)
    - **Evidence A:**
      - `EV-000065` — *official*, "Harborlight Cloud -- About" (2026-02-01) — https://harborlightcloud.com/about
  - Value B: "~90 employees" (reputable_news, 2025-10-01)
    - **Evidence B:**
      - `EV-000066` — *reputable_news*, "CloudWire -- Company Profile: Harborlight Cloud" (2025-10-01) — https://cloudwire.example.com/harborlight-profile
  - **Resolution:** must remain unresolved, requires human review

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000065` — *official*, "Harborlight Cloud -- About" (2026-02-01) — https://harborlightcloud.com/about
  - `EV-000066` — *reputable_news*, "CloudWire -- Company Profile: Harborlight Cloud" (2025-10-01) — https://cloudwire.example.com/harborlight-profile

---

## MR-045 — How many customers does Solace Metrics have?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Solace Metrics |
| **Research category** | `notable_customers` |
| **top_k** | 5 |
| **Case type** | CONFLICT |
| **Difficulty** | hard |
| **Primary metric** | Conflict-Resolution Correctness |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

### Gold conflicts
- **Field:** `notable_customers`
  - Value A: "2,000+ customers" (official, 2026-01-15)
    - **Evidence A:**
      - `EV-000067` — *official*, "Solace Metrics -- About" (2026-01-15) — https://solacemetrics.com/about
  - Value B: "~1,200 customers" (reputable_news, 2025-11-05)
    - **Evidence B:**
      - `EV-000068` — *reputable_news*, "SaaSToday -- Solace Metrics Growth Profile" (2025-11-05) — https://saastoday.example.com/solace-metrics-growth-profile
  - **Resolution:** must remain unresolved, requires human review

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000067` — *official*, "Solace Metrics -- About" (2026-01-15) — https://solacemetrics.com/about
  - `EV-000068` — *reputable_news*, "SaaSToday -- Solace Metrics Growth Profile" (2025-11-05) — https://saastoday.example.com/solace-metrics-growth-profile

---

## MR-046 — When did Anchorpoint AI launch its product?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Anchorpoint AI |
| **Research category** | `company_description` |
| **top_k** | 5 |
| **Case type** | CONFLICT |
| **Difficulty** | hard |
| **Primary metric** | Conflict-Resolution Correctness |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

### Gold conflicts
- **Field:** `company_description`
  - Value A: "Launched 2023" (official, 2026-01-01)
    - **Evidence A:**
      - `EV-000069` — *official*, "Anchorpoint AI -- About (company history)" (2026-01-01) — https://anchorpoint.ai/about
  - Value B: "Beta launched late 2022" (blog, 2025-04-01)
    - **Evidence B:**
      - `EV-000070` — *blog*, "TechArchive -- Anchorpoint AI's Early Days" (2025-04-01) — https://techarchive.example.com/anchorpoint-early-days
  - **Expected preferred value:** Launched 2023
  - **Expected resolution reason:** The official company account should be preferred over an unverified third-party retrospective, though the discrepancy (beta vs GA) is worth surfacing.

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000069` — *official*, "Anchorpoint AI -- About (company history)" (2026-01-01) — https://anchorpoint.ai/about
  - `EV-000070` — *blog*, "TechArchive -- Anchorpoint AI's Early Days" (2025-04-01) — https://techarchive.example.com/anchorpoint-early-days

---

## MR-047 — Is Cobalt Meridian an independent company or has it been acquired?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Cobalt Meridian |
| **Research category** | `company_description` |
| **top_k** | 5 |
| **Case type** | CONFLICT |
| **Difficulty** | medium |
| **Primary metric** | Conflict-Resolution Correctness |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

### Gold conflicts
- **Field:** `company_description`
  - Value A: "Independent, privately held" (official, 2025-12-01)
    - **Evidence A:**
      - `EV-000071` — *official*, "Cobalt Meridian -- About" (2025-12-01) — https://cobaltmeridian.com/about
  - Value B: "Acquired by Vantis Group" (reputable_news, 2026-04-20)
    - **Evidence B:**
      - `EV-000072` — *reputable_news*, "CloudWire -- Cobalt Meridian Acquired by Vantis Group" (2026-04-20) — https://cloudwire.example.com/cobalt-meridian-acquired-by-vantis
  - **Expected preferred value:** Acquired by Vantis Group
  - **Expected resolution reason:** The more recent, independently reported acquisition supersedes the stale 'about' page that predates the deal closing.

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000071` — *official*, "Cobalt Meridian -- About" (2025-12-01) — https://cobaltmeridian.com/about
  - `EV-000072` — *reputable_news*, "CloudWire -- Cobalt Meridian Acquired by Vantis Group" (2026-04-20) — https://cloudwire.example.com/cobalt-meridian-acquired-by-vantis

---

## MR-048 — Is Lumen Cascade SOC 2 Type II certified?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Lumen Cascade |
| **Research category** | `core_features` |
| **top_k** | 5 |
| **Case type** | CONFLICT |
| **Difficulty** | hard |
| **Primary metric** | Conflict-Resolution Correctness |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

### Gold conflicts
- **Field:** `core_features`
  - Value A: "SOC 2 Type II certified" (official, 2026-02-10)
    - **Evidence A:**
      - `EV-000073` — *official*, "Lumen Cascade -- Features" (2026-02-10) — https://lumencascade.com/features
  - Value B: "Not yet certified, audit in progress" (review, 2026-03-01)
    - **Evidence B:**
      - `EV-000074` — *review*, "PeerReviews -- Lumen Cascade Review" (2026-03-01) — https://peerreviews.example.com/lumen-cascade/review-5541
  - **Resolution:** must remain unresolved, requires human review

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000073` — *official*, "Lumen Cascade -- Features" (2026-02-10) — https://lumencascade.com/features
  - `EV-000074` — *review*, "PeerReviews -- Lumen Cascade Review" (2026-03-01) — https://peerreviews.example.com/lumen-cascade/review-5541

---

<a id="family-06"></a>

# Ground-Truth Coverage Cases (MR-049 – MR-053)

[↑ Back to top](#top)

Each scenario defines a set of individually-listed `gold_facts` spanning multiple categories for one competitor. Ground Truth Coverage = recovered gold facts / total gold facts, judged semantically (wording differs) by `judges/coverage_judge.py` and computed by `evaluators/coverage.py`. This is distinct from the agent's own `evidence_coverage_score` (which only checks "is this category non-empty").

**5 scenarios in this family: MR-049, MR-050, MR-051, MR-052, MR-053**

---

## MR-049 — Give a full profile of Northwind Analytics covering pricing, features, positioning, and recent activity.
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Northwind Analytics |
| **Research category** | `coverage_freshness` |
| **top_k** | 5 |
| **Case type** | COVERAGE_FRESHNESS |
| **Difficulty** | medium |
| **Primary metric** | Ground-Truth Coverage |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

### Gold facts

**pricing**
- `MR-049-F1` — Northwind Analytics charges $99/month with an annual discount option.
  - **Evidence:**
    - `EV-000075` — *official*, "Northwind Analytics -- Pricing" (2026-03-01) — https://northwindanalytics.example.com/pricing

**core_features**
- `MR-049-F2` — Northwind Analytics offers dashboards, scheduled reports, and role-based access control.
  - **Evidence:**
    - `EV-000076` — *documentation*, "Northwind Analytics Documentation -- Core Features" (2026-02-15) — https://docs.northwindanalytics.example.com/features

**target_customers**
- `MR-049-F3` — Northwind Analytics targets growth-stage B2B companies without a dedicated analytics engineer.
  - **Evidence:**
    - `EV-000077` — *official*, "Northwind Analytics -- Who It's For" (2026-01-20) — https://northwindanalytics.example.com/customers

**positioning**
- `MR-049-F4` — Northwind Analytics positions itself as the fastest-to-deploy option, emphasizing same-day onboarding.
  - **Evidence:**
    - `EV-000078` — *official*, "Northwind Analytics -- Positioning" (2026-02-01) — https://northwindanalytics.example.com/about

**differentiators**
- `MR-049-F5` — Northwind Analytics's standout capability is one-click migration from spreadsheets.
  - **Evidence:**
    - `EV-000079` — *reputable_news*, "SaaSToday -- Northwind Analytics Review" (2026-03-10) — https://saastoday.example.com/northwindanalytics-review

**announcements**
- `MR-049-F6` — Northwind Analytics announced a new native billing-platform integration.
  - **Evidence:**
    - `EV-000080` — *official*, "Northwind Analytics -- New Integration Announced" (2026-04-01) — https://northwindanalytics.example.com/blog/new-integration

**free_trial**
- `MR-049-F7` — Northwind Analytics offers a 14-day free trial, no credit card required.
  - **Evidence:**
    - `EV-000082` — *official*, "Northwind Analytics -- Free Trial" (2026-03-20) — https://northwindanalytics.example.com/trial

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000075` — *official*, "Northwind Analytics -- Pricing" (2026-03-01) — https://northwindanalytics.example.com/pricing
  - `EV-000076` — *documentation*, "Northwind Analytics Documentation -- Core Features" (2026-02-15) — https://docs.northwindanalytics.example.com/features
  - `EV-000077` — *official*, "Northwind Analytics -- Who It's For" (2026-01-20) — https://northwindanalytics.example.com/customers
  - `EV-000078` — *official*, "Northwind Analytics -- Positioning" (2026-02-01) — https://northwindanalytics.example.com/about
  - `EV-000079` — *reputable_news*, "SaaSToday -- Northwind Analytics Review" (2026-03-10) — https://saastoday.example.com/northwindanalytics-review
  - `EV-000080` — *official*, "Northwind Analytics -- New Integration Announced" (2026-04-01) — https://northwindanalytics.example.com/blog/new-integration
  - `EV-000081` — *reputable_news*, "CloudWire -- Northwind Analytics Hits Growth Milestone" (2026-04-15) — https://cloudwire.example.com/northwindanalytics-milestone
  - `EV-000082` — *official*, "Northwind Analytics -- Free Trial" (2026-03-20) — https://northwindanalytics.example.com/trial
  - `EV-000083` — *review*, "PeerReviews -- Northwind Analytics Summary" (2026-03-25) — https://peerreviews.example.com/northwindanalytics/summary
  - `EV-000084` — *official*, "Northwind Analytics -- Case Studies" (2026-02-20) — https://northwindanalytics.example.com/customers/case-studies
- **Required:**
  - `EV-000075` — *official*, "Northwind Analytics -- Pricing" (2026-03-01) — https://northwindanalytics.example.com/pricing
  - `EV-000076` — *documentation*, "Northwind Analytics Documentation -- Core Features" (2026-02-15) — https://docs.northwindanalytics.example.com/features
  - `EV-000077` — *official*, "Northwind Analytics -- Who It's For" (2026-01-20) — https://northwindanalytics.example.com/customers
  - `EV-000078` — *official*, "Northwind Analytics -- Positioning" (2026-02-01) — https://northwindanalytics.example.com/about
  - `EV-000079` — *reputable_news*, "SaaSToday -- Northwind Analytics Review" (2026-03-10) — https://saastoday.example.com/northwindanalytics-review
  - `EV-000080` — *official*, "Northwind Analytics -- New Integration Announced" (2026-04-01) — https://northwindanalytics.example.com/blog/new-integration
  - `EV-000081` — *reputable_news*, "CloudWire -- Northwind Analytics Hits Growth Milestone" (2026-04-15) — https://cloudwire.example.com/northwindanalytics-milestone

---

## MR-050 — Give a full profile of Vantage Loop covering pricing, features, positioning, and recent activity.
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Vantage Loop |
| **Research category** | `coverage_freshness` |
| **top_k** | 5 |
| **Case type** | COVERAGE_FRESHNESS |
| **Difficulty** | medium |
| **Primary metric** | Ground-Truth Coverage |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

### Gold facts

**pricing**
- `MR-050-F1` — Vantage Loop charges $99/month with an annual discount option.
  - **Evidence:**
    - `EV-000085` — *official*, "Vantage Loop -- Pricing" (2026-03-01) — https://vantageloop.example.com/pricing

**core_features**
- `MR-050-F2` — Vantage Loop offers dashboards, scheduled reports, and role-based access control.
  - **Evidence:**
    - `EV-000086` — *documentation*, "Vantage Loop Documentation -- Core Features" (2026-02-15) — https://docs.vantageloop.example.com/features

**target_customers**
- `MR-050-F3` — Vantage Loop targets growth-stage B2B companies without a dedicated analytics engineer.
  - **Evidence:**
    - `EV-000087` — *official*, "Vantage Loop -- Who It's For" (2026-01-20) — https://vantageloop.example.com/customers

**positioning**
- `MR-050-F4` — Vantage Loop positions itself as the fastest-to-deploy option, emphasizing same-day onboarding.
  - **Evidence:**
    - `EV-000088` — *official*, "Vantage Loop -- Positioning" (2026-02-01) — https://vantageloop.example.com/about

**differentiators**
- `MR-050-F5` — Vantage Loop's standout capability is one-click migration from spreadsheets.
  - **Evidence:**
    - `EV-000089` — *reputable_news*, "SaaSToday -- Vantage Loop Review" (2026-03-10) — https://saastoday.example.com/vantageloop-review

**announcements**
- `MR-050-F6` — Vantage Loop announced a new native billing-platform integration.
  - **Evidence:**
    - `EV-000090` — *official*, "Vantage Loop -- New Integration Announced" (2026-04-01) — https://vantageloop.example.com/blog/new-integration

**free_trial**
- `MR-050-F7` — Vantage Loop offers a 14-day free trial, no credit card required.
  - **Evidence:**
    - `EV-000092` — *official*, "Vantage Loop -- Free Trial" (2026-03-20) — https://vantageloop.example.com/trial

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000085` — *official*, "Vantage Loop -- Pricing" (2026-03-01) — https://vantageloop.example.com/pricing
  - `EV-000086` — *documentation*, "Vantage Loop Documentation -- Core Features" (2026-02-15) — https://docs.vantageloop.example.com/features
  - `EV-000087` — *official*, "Vantage Loop -- Who It's For" (2026-01-20) — https://vantageloop.example.com/customers
  - `EV-000088` — *official*, "Vantage Loop -- Positioning" (2026-02-01) — https://vantageloop.example.com/about
  - `EV-000089` — *reputable_news*, "SaaSToday -- Vantage Loop Review" (2026-03-10) — https://saastoday.example.com/vantageloop-review
  - `EV-000090` — *official*, "Vantage Loop -- New Integration Announced" (2026-04-01) — https://vantageloop.example.com/blog/new-integration
  - `EV-000091` — *reputable_news*, "CloudWire -- Vantage Loop Hits Growth Milestone" (2026-04-15) — https://cloudwire.example.com/vantageloop-milestone
  - `EV-000092` — *official*, "Vantage Loop -- Free Trial" (2026-03-20) — https://vantageloop.example.com/trial
  - `EV-000093` — *review*, "PeerReviews -- Vantage Loop Summary" (2026-03-25) — https://peerreviews.example.com/vantageloop/summary
  - `EV-000094` — *official*, "Vantage Loop -- Case Studies" (2026-02-20) — https://vantageloop.example.com/customers/case-studies
- **Required:**
  - `EV-000085` — *official*, "Vantage Loop -- Pricing" (2026-03-01) — https://vantageloop.example.com/pricing
  - `EV-000086` — *documentation*, "Vantage Loop Documentation -- Core Features" (2026-02-15) — https://docs.vantageloop.example.com/features
  - `EV-000087` — *official*, "Vantage Loop -- Who It's For" (2026-01-20) — https://vantageloop.example.com/customers
  - `EV-000088` — *official*, "Vantage Loop -- Positioning" (2026-02-01) — https://vantageloop.example.com/about
  - `EV-000089` — *reputable_news*, "SaaSToday -- Vantage Loop Review" (2026-03-10) — https://saastoday.example.com/vantageloop-review
  - `EV-000090` — *official*, "Vantage Loop -- New Integration Announced" (2026-04-01) — https://vantageloop.example.com/blog/new-integration
  - `EV-000091` — *reputable_news*, "CloudWire -- Vantage Loop Hits Growth Milestone" (2026-04-15) — https://cloudwire.example.com/vantageloop-milestone

---

## MR-051 — Give a full profile of Cobalt Meridian covering pricing, features, positioning, and recent activity.
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Cobalt Meridian |
| **Research category** | `coverage_freshness` |
| **top_k** | 5 |
| **Case type** | COVERAGE_FRESHNESS |
| **Difficulty** | medium |
| **Primary metric** | Ground-Truth Coverage |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

### Gold facts

**pricing**
- `MR-051-F1` — Cobalt Meridian charges $99/month with an annual discount option.
  - **Evidence:**
    - `EV-000095` — *official*, "Cobalt Meridian -- Pricing" (2026-03-01) — https://cobaltmeridian.example.com/pricing

**core_features**
- `MR-051-F2` — Cobalt Meridian offers dashboards, scheduled reports, and role-based access control.
  - **Evidence:**
    - `EV-000096` — *documentation*, "Cobalt Meridian Documentation -- Core Features" (2026-02-15) — https://docs.cobaltmeridian.example.com/features

**target_customers**
- `MR-051-F3` — Cobalt Meridian targets growth-stage B2B companies without a dedicated analytics engineer.
  - **Evidence:**
    - `EV-000097` — *official*, "Cobalt Meridian -- Who It's For" (2026-01-20) — https://cobaltmeridian.example.com/customers

**positioning**
- `MR-051-F4` — Cobalt Meridian positions itself as the fastest-to-deploy option, emphasizing same-day onboarding.
  - **Evidence:**
    - `EV-000098` — *official*, "Cobalt Meridian -- Positioning" (2026-02-01) — https://cobaltmeridian.example.com/about

**differentiators**
- `MR-051-F5` — Cobalt Meridian's standout capability is one-click migration from spreadsheets.
  - **Evidence:**
    - `EV-000099` — *reputable_news*, "SaaSToday -- Cobalt Meridian Review" (2026-03-10) — https://saastoday.example.com/cobaltmeridian-review

**announcements**
- `MR-051-F6` — Cobalt Meridian announced a new native billing-platform integration.
  - **Evidence:**
    - `EV-000100` — *official*, "Cobalt Meridian -- New Integration Announced" (2026-04-01) — https://cobaltmeridian.example.com/blog/new-integration

**free_trial**
- `MR-051-F7` — Cobalt Meridian offers a 14-day free trial, no credit card required.
  - **Evidence:**
    - `EV-000102` — *official*, "Cobalt Meridian -- Free Trial" (2026-03-20) — https://cobaltmeridian.example.com/trial

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000095` — *official*, "Cobalt Meridian -- Pricing" (2026-03-01) — https://cobaltmeridian.example.com/pricing
  - `EV-000096` — *documentation*, "Cobalt Meridian Documentation -- Core Features" (2026-02-15) — https://docs.cobaltmeridian.example.com/features
  - `EV-000097` — *official*, "Cobalt Meridian -- Who It's For" (2026-01-20) — https://cobaltmeridian.example.com/customers
  - `EV-000098` — *official*, "Cobalt Meridian -- Positioning" (2026-02-01) — https://cobaltmeridian.example.com/about
  - `EV-000099` — *reputable_news*, "SaaSToday -- Cobalt Meridian Review" (2026-03-10) — https://saastoday.example.com/cobaltmeridian-review
  - `EV-000100` — *official*, "Cobalt Meridian -- New Integration Announced" (2026-04-01) — https://cobaltmeridian.example.com/blog/new-integration
  - `EV-000101` — *reputable_news*, "CloudWire -- Cobalt Meridian Hits Growth Milestone" (2026-04-15) — https://cloudwire.example.com/cobaltmeridian-milestone
  - `EV-000102` — *official*, "Cobalt Meridian -- Free Trial" (2026-03-20) — https://cobaltmeridian.example.com/trial
  - `EV-000103` — *review*, "PeerReviews -- Cobalt Meridian Summary" (2026-03-25) — https://peerreviews.example.com/cobaltmeridian/summary
  - `EV-000104` — *official*, "Cobalt Meridian -- Case Studies" (2026-02-20) — https://cobaltmeridian.example.com/customers/case-studies
- **Required:**
  - `EV-000095` — *official*, "Cobalt Meridian -- Pricing" (2026-03-01) — https://cobaltmeridian.example.com/pricing
  - `EV-000096` — *documentation*, "Cobalt Meridian Documentation -- Core Features" (2026-02-15) — https://docs.cobaltmeridian.example.com/features
  - `EV-000097` — *official*, "Cobalt Meridian -- Who It's For" (2026-01-20) — https://cobaltmeridian.example.com/customers
  - `EV-000098` — *official*, "Cobalt Meridian -- Positioning" (2026-02-01) — https://cobaltmeridian.example.com/about
  - `EV-000099` — *reputable_news*, "SaaSToday -- Cobalt Meridian Review" (2026-03-10) — https://saastoday.example.com/cobaltmeridian-review
  - `EV-000100` — *official*, "Cobalt Meridian -- New Integration Announced" (2026-04-01) — https://cobaltmeridian.example.com/blog/new-integration
  - `EV-000101` — *reputable_news*, "CloudWire -- Cobalt Meridian Hits Growth Milestone" (2026-04-15) — https://cloudwire.example.com/cobaltmeridian-milestone

---

## MR-052 — Give a full profile of Fernbridge Data covering pricing, features, positioning, and recent activity.
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Fernbridge Data |
| **Research category** | `coverage_freshness` |
| **top_k** | 5 |
| **Case type** | COVERAGE_FRESHNESS |
| **Difficulty** | medium |
| **Primary metric** | Ground-Truth Coverage |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

### Gold facts

**pricing**
- `MR-052-F1` — Fernbridge Data charges $99/month with an annual discount option.
  - **Evidence:**
    - `EV-000105` — *official*, "Fernbridge Data -- Pricing" (2026-03-01) — https://fernbridgedata.example.com/pricing

**core_features**
- `MR-052-F2` — Fernbridge Data offers dashboards, scheduled reports, and role-based access control.
  - **Evidence:**
    - `EV-000106` — *documentation*, "Fernbridge Data Documentation -- Core Features" (2026-02-15) — https://docs.fernbridgedata.example.com/features

**target_customers**
- `MR-052-F3` — Fernbridge Data targets growth-stage B2B companies without a dedicated analytics engineer.
  - **Evidence:**
    - `EV-000107` — *official*, "Fernbridge Data -- Who It's For" (2026-01-20) — https://fernbridgedata.example.com/customers

**positioning**
- `MR-052-F4` — Fernbridge Data positions itself as the fastest-to-deploy option, emphasizing same-day onboarding.
  - **Evidence:**
    - `EV-000108` — *official*, "Fernbridge Data -- Positioning" (2026-02-01) — https://fernbridgedata.example.com/about

**differentiators**
- `MR-052-F5` — Fernbridge Data's standout capability is one-click migration from spreadsheets.
  - **Evidence:**
    - `EV-000109` — *reputable_news*, "SaaSToday -- Fernbridge Data Review" (2026-03-10) — https://saastoday.example.com/fernbridgedata-review

**announcements**
- `MR-052-F6` — Fernbridge Data announced a new native billing-platform integration.
  - **Evidence:**
    - `EV-000110` — *official*, "Fernbridge Data -- New Integration Announced" (2026-04-01) — https://fernbridgedata.example.com/blog/new-integration

**free_trial**
- `MR-052-F7` — Fernbridge Data offers a 14-day free trial, no credit card required.
  - **Evidence:**
    - `EV-000112` — *official*, "Fernbridge Data -- Free Trial" (2026-03-20) — https://fernbridgedata.example.com/trial

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000105` — *official*, "Fernbridge Data -- Pricing" (2026-03-01) — https://fernbridgedata.example.com/pricing
  - `EV-000106` — *documentation*, "Fernbridge Data Documentation -- Core Features" (2026-02-15) — https://docs.fernbridgedata.example.com/features
  - `EV-000107` — *official*, "Fernbridge Data -- Who It's For" (2026-01-20) — https://fernbridgedata.example.com/customers
  - `EV-000108` — *official*, "Fernbridge Data -- Positioning" (2026-02-01) — https://fernbridgedata.example.com/about
  - `EV-000109` — *reputable_news*, "SaaSToday -- Fernbridge Data Review" (2026-03-10) — https://saastoday.example.com/fernbridgedata-review
  - `EV-000110` — *official*, "Fernbridge Data -- New Integration Announced" (2026-04-01) — https://fernbridgedata.example.com/blog/new-integration
  - `EV-000111` — *reputable_news*, "CloudWire -- Fernbridge Data Hits Growth Milestone" (2026-04-15) — https://cloudwire.example.com/fernbridgedata-milestone
  - `EV-000112` — *official*, "Fernbridge Data -- Free Trial" (2026-03-20) — https://fernbridgedata.example.com/trial
  - `EV-000113` — *review*, "PeerReviews -- Fernbridge Data Summary" (2026-03-25) — https://peerreviews.example.com/fernbridgedata/summary
  - `EV-000114` — *official*, "Fernbridge Data -- Case Studies" (2026-02-20) — https://fernbridgedata.example.com/customers/case-studies
- **Required:**
  - `EV-000105` — *official*, "Fernbridge Data -- Pricing" (2026-03-01) — https://fernbridgedata.example.com/pricing
  - `EV-000106` — *documentation*, "Fernbridge Data Documentation -- Core Features" (2026-02-15) — https://docs.fernbridgedata.example.com/features
  - `EV-000107` — *official*, "Fernbridge Data -- Who It's For" (2026-01-20) — https://fernbridgedata.example.com/customers
  - `EV-000108` — *official*, "Fernbridge Data -- Positioning" (2026-02-01) — https://fernbridgedata.example.com/about
  - `EV-000109` — *reputable_news*, "SaaSToday -- Fernbridge Data Review" (2026-03-10) — https://saastoday.example.com/fernbridgedata-review
  - `EV-000110` — *official*, "Fernbridge Data -- New Integration Announced" (2026-04-01) — https://fernbridgedata.example.com/blog/new-integration
  - `EV-000111` — *reputable_news*, "CloudWire -- Fernbridge Data Hits Growth Milestone" (2026-04-15) — https://cloudwire.example.com/fernbridgedata-milestone

---

## MR-053 — Give a full profile of Solace Metrics covering pricing, features, positioning, and recent activity.
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Solace Metrics |
| **Research category** | `coverage_freshness` |
| **top_k** | 5 |
| **Case type** | COVERAGE_FRESHNESS |
| **Difficulty** | medium |
| **Primary metric** | Ground-Truth Coverage |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

### Gold facts

**pricing**
- `MR-053-F1` — Solace Metrics charges $99/month with an annual discount option.
  - **Evidence:**
    - `EV-000115` — *official*, "Solace Metrics -- Pricing" (2026-03-01) — https://solacemetrics.example.com/pricing

**core_features**
- `MR-053-F2` — Solace Metrics offers dashboards, scheduled reports, and role-based access control.
  - **Evidence:**
    - `EV-000116` — *documentation*, "Solace Metrics Documentation -- Core Features" (2026-02-15) — https://docs.solacemetrics.example.com/features

**target_customers**
- `MR-053-F3` — Solace Metrics targets growth-stage B2B companies without a dedicated analytics engineer.
  - **Evidence:**
    - `EV-000117` — *official*, "Solace Metrics -- Who It's For" (2026-01-20) — https://solacemetrics.example.com/customers

**positioning**
- `MR-053-F4` — Solace Metrics positions itself as the fastest-to-deploy option, emphasizing same-day onboarding.
  - **Evidence:**
    - `EV-000118` — *official*, "Solace Metrics -- Positioning" (2026-02-01) — https://solacemetrics.example.com/about

**differentiators**
- `MR-053-F5` — Solace Metrics's standout capability is one-click migration from spreadsheets.
  - **Evidence:**
    - `EV-000119` — *reputable_news*, "SaaSToday -- Solace Metrics Review" (2026-03-10) — https://saastoday.example.com/solacemetrics-review

**announcements**
- `MR-053-F6` — Solace Metrics announced a new native billing-platform integration.
  - **Evidence:**
    - `EV-000120` — *official*, "Solace Metrics -- New Integration Announced" (2026-04-01) — https://solacemetrics.example.com/blog/new-integration

**free_trial**
- `MR-053-F7` — Solace Metrics offers a 14-day free trial, no credit card required.
  - **Evidence:**
    - `EV-000122` — *official*, "Solace Metrics -- Free Trial" (2026-03-20) — https://solacemetrics.example.com/trial

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000115` — *official*, "Solace Metrics -- Pricing" (2026-03-01) — https://solacemetrics.example.com/pricing
  - `EV-000116` — *documentation*, "Solace Metrics Documentation -- Core Features" (2026-02-15) — https://docs.solacemetrics.example.com/features
  - `EV-000117` — *official*, "Solace Metrics -- Who It's For" (2026-01-20) — https://solacemetrics.example.com/customers
  - `EV-000118` — *official*, "Solace Metrics -- Positioning" (2026-02-01) — https://solacemetrics.example.com/about
  - `EV-000119` — *reputable_news*, "SaaSToday -- Solace Metrics Review" (2026-03-10) — https://saastoday.example.com/solacemetrics-review
  - `EV-000120` — *official*, "Solace Metrics -- New Integration Announced" (2026-04-01) — https://solacemetrics.example.com/blog/new-integration
  - `EV-000121` — *reputable_news*, "CloudWire -- Solace Metrics Hits Growth Milestone" (2026-04-15) — https://cloudwire.example.com/solacemetrics-milestone
  - `EV-000122` — *official*, "Solace Metrics -- Free Trial" (2026-03-20) — https://solacemetrics.example.com/trial
  - `EV-000123` — *review*, "PeerReviews -- Solace Metrics Summary" (2026-03-25) — https://peerreviews.example.com/solacemetrics/summary
  - `EV-000124` — *official*, "Solace Metrics -- Case Studies" (2026-02-20) — https://solacemetrics.example.com/customers/case-studies
- **Required:**
  - `EV-000115` — *official*, "Solace Metrics -- Pricing" (2026-03-01) — https://solacemetrics.example.com/pricing
  - `EV-000116` — *documentation*, "Solace Metrics Documentation -- Core Features" (2026-02-15) — https://docs.solacemetrics.example.com/features
  - `EV-000117` — *official*, "Solace Metrics -- Who It's For" (2026-01-20) — https://solacemetrics.example.com/customers
  - `EV-000118` — *official*, "Solace Metrics -- Positioning" (2026-02-01) — https://solacemetrics.example.com/about
  - `EV-000119` — *reputable_news*, "SaaSToday -- Solace Metrics Review" (2026-03-10) — https://saastoday.example.com/solacemetrics-review
  - `EV-000120` — *official*, "Solace Metrics -- New Integration Announced" (2026-04-01) — https://solacemetrics.example.com/blog/new-integration
  - `EV-000121` — *reputable_news*, "CloudWire -- Solace Metrics Hits Growth Milestone" (2026-04-15) — https://cloudwire.example.com/solacemetrics-milestone

---

<a id="family-07"></a>

# Cost-Projection Cases (MR-054 – MR-055)

[↑ Back to top](#top)

Checks projected cost (pre-flight estimate from `cost_service.project_cost`) against a plausible actual-cost band for a research run of a given size. Scored via `evaluators/cost_accuracy.py` (`cost_error`, `cost_gate_status`); release gate requires ≤20% error (required) / ≤10% (preferred).

**2 scenarios in this family: MR-054, MR-055**

---

## MR-054 — What should a research run analyzing these 2 competitors cost?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Northwind Analytics, Vantage Loop |
| **Research category** | `cost_projection` |
| **top_k** | 5 |
| **Case type** | COST |
| **Difficulty** | medium |
| **Primary metric** | cost_projection_error |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

**Expected cost range:** $0.80 – $1.60

---

## MR-055 — What should a research run analyzing these 3 competitors cost?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Cobalt Meridian, Fernbridge Data, Solace Metrics |
| **Research category** | `cost_projection` |
| **top_k** | 5 |
| **Case type** | COST |
| **Difficulty** | medium |
| **Primary metric** | cost_projection_error |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

**Expected cost range:** $1.20 – $2.40

---

<a id="family-08"></a>

# Temporal / Freshness Cases (MR-056 – MR-058)

[↑ Back to top](#top)

Evidence for both an old and a new value exists in the corpus with different `published_at` dates. The agent must resolve to the *current* value while still preserving the historical one as evidence, not silently presenting a stale value as current. Judged by `judges/freshness_judge.py` on the 0-3 rubric, aggregated via `evaluators/freshness.py`.

**3 scenarios in this family: MR-056, MR-057, MR-058**

---

## MR-056 — What is Northwind Analytics' current price, given it changed over the past year?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Northwind Analytics |
| **Research category** | `pricing` |
| **top_k** | 5 |
| **Case type** | TEMPORAL |
| **Difficulty** | medium |
| **Primary metric** | Temporal/Freshness Correctness |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

**Expected current value(s):**
- `pricing` → $149/seat/month

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000125` — *official*, "Northwind Analytics -- Pricing (2025 archive)" (2025-06-01) — https://web.archive.example.com/northwindanalytics-2025
  - `EV-000126` — *official*, "Northwind Analytics -- Current Pricing" (2026-02-01) — https://northwindanalytics.io/pricing
- **Required:**
  - `EV-000126` — *official*, "Northwind Analytics -- Current Pricing" (2026-02-01) — https://northwindanalytics.io/pricing

---

## MR-057 — Is Vantage Loop's 'Classic Reports' feature still current?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Vantage Loop |
| **Research category** | `core_features` |
| **top_k** | 5 |
| **Case type** | TEMPORAL |
| **Difficulty** | hard |
| **Primary metric** | Temporal/Freshness Correctness |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

**Expected current value(s):**
- `core_features` → Classic Reports removed, replaced by Dashboards

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000127` — *blog*, "Vantage Loop -- Features (cached 2025 copy)" (2025-09-01) — https://mirror-cache.example.com/vantage-loop-features-2025
  - `EV-000128` — *documentation*, "Vantage Loop Changelog -- January 2026" (2026-01-15) — https://docs.vantageloop.com/changelog/2026-01
- **Required:**
  - `EV-000128` — *documentation*, "Vantage Loop Changelog -- January 2026" (2026-01-15) — https://docs.vantageloop.com/changelog/2026-01

---

## MR-058 — How has Anchorpoint AI's market positioning evolved, and what is it now?
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Anchorpoint AI |
| **Research category** | `positioning` |
| **top_k** | 5 |
| **Case type** | TEMPORAL |
| **Difficulty** | medium |
| **Primary metric** | Temporal/Freshness Correctness |
| **Gold version** | gold-v1 |

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

**Expected current value(s):**
- `positioning` → Accuracy/verifiability-first, not speed-first

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000129` — *blog*, "TechArchive -- Anchorpoint AI in 2024" (2024-05-01) — https://techarchive.example.com/anchorpoint-2024-positioning
  - `EV-000130` — *official*, "Anchorpoint AI -- About (current)" (2026-01-20) — https://anchorpoint.ai/about
- **Required:**
  - `EV-000130` — *official*, "Anchorpoint AI -- About (current)" (2026-01-20) — https://anchorpoint.ai/about

---

<a id="family-09"></a>

# Resilience / Latency Cases (MR-059 – MR-060)

[↑ Back to top](#top)

Simulated partial-system failure (one competitor branch fails; or slow search/LLM/retrieval to exercise latency measurement). The rest of the run must still complete, the failed branch must be explicitly marked failed/partial with no invented facts, and — for the latency scenario — this is where repeated executions (60×1/60×3/60×5) feed the p95/p99 latency calculation. Checked by `evaluators/partial_failure.py` and `evaluators/latency.py`.

**2 scenarios in this family: MR-059, MR-060**

---

## MR-059 — Research these 2 competitors, given that one of their web-research branches will fail.
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Northwind Analytics, Harborlight Cloud |
| **Research category** | `resilience` |
| **top_k** | 5 |
| **Case type** | RESILIENCE |
| **Difficulty** | hard |
| **Primary metric** | partial_failure_correctness |
| **Gold version** | gold-v1 |

**Simulation parameters:** `{"fail_competitor": "Harborlight Cloud"}`

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

**Expected abstention:**
- Harborlight Cloud branch must be marked failed/partial with no invented facts
- Unknown

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000131` — *official*, "Northwind Analytics -- Pricing" (2026-05-01) — https://northwindanalytics.io/pricing

---

## MR-060 — Research this competitor under simulated slow search/LLM latency conditions.
| | |
|---|---|
| **Target company** | Pipeline Harbor |
| **Competitor(s)** | Vantage Loop |
| **Research category** | `resilience` |
| **top_k** | 5 |
| **Case type** | RESILIENCE |
| **Difficulty** | medium |
| **Primary metric** | p95_latency_seconds |
| **Gold version** | gold-v1 |

**Simulation parameters:** `{"inject_latency_seconds": 25}`

### Expected answer
_(no single expected claim — see gold facts / red flags / conflicts below)_

### Relevant evidence (retrieval ground truth)
- **Relevant:**
  - `EV-000132` — *official*, "Vantage Loop -- Plans & Pricing" (2026-05-01) — https://vantageloop.com/plans

---

