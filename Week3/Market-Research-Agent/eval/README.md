# LLM-quality eval suite

This is **not** the pytest suite (`tests/`). `tests/` answers "does the code
behave correctly given fake inputs" and runs by default with zero live
credentials. This directory answers a different question — "is the actual
LLM output any good" — and requires real credentials. It never runs as part
of `uv run pytest` and is never run automatically.

## What it checks

- **Discovery quality** (`run_discovery_eval.py`): for a handful of example
  research requests (`datasets/discovery_examples.json`), scores whether the
  5 returned competitors are actually relevant, correctly classified
  (direct/indirect/emerging), and structurally valid (exactly 5, scores in
  0–1). Relevance/classification are scored by an LLM-as-judge evaluator;
  the structural checks are plain Python.
- **Analysis quality** (`run_analysis_eval.py`): runs the Analysis and
  Verification Agent against a small fixture set of pre-fetched evidence
  (not a live web crawl, to keep this fast and cheap) and checks:
  - **Groundedness** (programmatic, not LLM-judged): every claim's
    `evidence_ids` must resolve to evidence that was actually retrieved —
    this catches a hallucinated citation directly, no judgment call needed.
  - **Faithfulness** (LLM-as-judge): does the claim text say what the cited
    evidence says, or does it over-claim beyond it?
  - **Coverage sanity**: the reported `evidence_coverage_score` matches the
    deterministic formula in `app/services/analysis_service.py`.

Both scripts call `langsmith.evaluate()` against the **real** agents (not the
`tests/` fakes), upload the dataset to LangSmith on first run if it isn't
there yet, and print a link to the results in the LangSmith UI.

## Requirements

- `OPENAI_API_KEY` and `LANGCHAIN_API_KEY` at minimum (both real).
- `run_analysis_eval.py` additionally needs `PINECONE_API_KEY` (it upserts
  the fixture evidence into a scratch namespace before querying it back out,
  the same way the real Web Research Agent → Analysis Agent handoff works).
- `run_discovery_eval.py` defaults to a fixture set of raw search results
  (no You.com key needed). Pass `--live` to instead call the real You.com API
  for a fully live discovery run — this needs `YOUCOM_API_KEY` too.

## Running it

```bash
uv run python eval/run_discovery_eval.py
uv run python eval/run_discovery_eval.py --live   # real You.com calls
uv run python eval/run_analysis_eval.py
```

Each prints an experiment URL on langsmith.com once it finishes. Nothing here
is wired into CI — run it manually whenever you want a read on quality after
changing a prompt, model, or retrieval strategy.

## Future AGI (optional second judge, runs alongside LangSmith)

`run_discovery_eval_futureagi.py` and `run_analysis_eval_futureagi.py` check
the same two agents using Future AGI's `evaluate()` instead of LangSmith's —
by explicit product decision this is a **second, independent** quality
signal, not a replacement for the LangSmith scripts above. Both keep running.

- Requires the optional `futureagi` uv dependency group:
  `uv sync --group futureagi`.
- Requires `FI_API_KEY` / `FI_SECRET_KEY` (real credentials — get them at
  futureagi.com). `run_analysis_eval_futureagi.py` additionally needs
  `PINECONE_API_KEY`, same as its LangSmith counterpart.
- Uses only metric identifiers ("faithfulness", "answer_relevancy")
  confirmed verbatim in Future AGI's own published code samples — more
  semantically precise built-in metrics (e.g. "detect_hallucination",
  "context_relevance") exist per their docs but their exact callable
  identifier strings weren't confirmed, so they were deliberately not
  guessed. See the docstring in `run_discovery_eval_futureagi.py`.
- If `FUTUREAGI_ENABLED=true` is also set, these runs additionally show up
  as traces in the Future AGI dashboard (via `init_futureagi_tracing()`),
  the same way any other run would.

```bash
uv sync --group futureagi
uv run python eval/run_discovery_eval_futureagi.py
uv run python eval/run_analysis_eval_futureagi.py
```

**Not yet live-tested against a real Future AGI account** in this codebase —
built from their published docs and code samples only, the same starting
point You.com's client had before a live test caught a real endpoint-shape
bug. Re-verify the first time real `FI_API_KEY`/`FI_SECRET_KEY` are available.

## Simulation: batch edge-case scenarios (`eval/simulation/`)

Future AGI's own simulation product (`agent-simulate`, personas, multi-turn
`TestRunner`) is built for conversational/voice agents. This app's pipeline
is a bounded, single-shot research run, not a chat loop, so rather than
force-fit an undocumented `agent_callback` contract onto it,
`eval/simulation/run_simulation.py` takes a more modest, honest approach:
it batch-drives a set of synthetic edge-case research requests
(`eval/simulation/scenarios.py`) through the real Discovery, Web Research,
and Analysis & Verification agents end-to-end, against real providers,
writing real rows through the same audit tables a live run would — then
checks structural expectations (candidate count, whether the budget gate
should have tripped, whether coverage stayed non-zero) and cross-checks
each competitor summary with Future AGI's `evaluate("answer_relevancy", ...)`.

Scenarios currently cover: an ambiguous one-word industry, a company with
likely-sparse public information, a non-English company name, and a request
engineered to trip the budget-approval gate.

Needs the same live credentials as `run_simulation.py`'s underlying
agents (`OPENAI_API_KEY`, `YOUCOM_API_KEY`, `PINECONE_API_KEY`) plus a
reachable `DATABASE_URL` — **it writes real `runs`/`discovery_candidates`/
`research_evidence` rows**, so point `DATABASE_URL` at a scratch/dev
database, not one you need to keep clean. `SERPER_API_KEY`/`SERPER_ENABLED`
and `FI_API_KEY`/`FI_SECRET_KEY` are optional on top of that.

```bash
uv sync --group futureagi
uv run python eval/simulation/run_simulation.py
uv run python eval/simulation/run_simulation.py --scenario budget_gate_trigger
```

## Golden Dataset / Frozen Evidence Corpus release evaluation (`eval/run.py`)

This is a **third, separate** eval surface from everything above. The scripts
above ask "is a single agent's output any good on a handful of examples";
this one asks the release-gate question: "across a fixed 60-scenario Golden
Dataset, does the whole Analysis pipeline still meet every quality/retrieval/
cost/latency/resilience bar before we ship?"

### What the two datasets are

- **Golden Dataset** (`eval/datasets/golden_scenarios.jsonl`, 60 scenarios,
  `eval.schemas.eval_models.GoldenScenario`) — one scenario per line: the
  `inputs` (target company, competitor(s), question, research category,
  simulation knobs), the `reference_outputs` (expected claims, gold red
  flags, gold conflicts, gold facts, expected unknowns/current values,
  expected cost range), and `metadata` (`case_type` — PASS / RETRIEVAL /
  RED_FLAG / MISSING_INFO / CONFLICT / COVERAGE_FRESHNESS / COST / TEMPORAL /
  RESILIENCE — plus difficulty, primary metric, and `gold_version`).
- **Frozen Evidence Corpus** (`eval/datasets/frozen_evidence.jsonl`,
  `eval.schemas.eval_models.EvidenceRecord`) — the fixed, hash-verified
  evidence text every scenario's `expected_*`/`gold_*` fields are computed
  against. "Frozen" means this is *not* a live web crawl — evidence is
  seeded directly into a scratch Pinecone namespace so a scenario's expected
  answer never drifts because You.com/Serper returned something different
  today.

Both are generated (and owned) by `eval/datasets/generate_golden_dataset.py`
— this eval surface only *reads* them.

### Frozen vs. live mode

`eval/run.py --mode frozen` (the only mode currently implemented) runs the
real `AnalysisVerificationAgent` against the frozen evidence — real OpenAI
+ Pinecone calls, no live search provider — the same fixture-seeding pattern
`run_analysis_eval.py` uses for its own dataset. `--mode live` is reserved
for eventually running the same 60 scenarios through a full live
Discovery → Web Research → Analysis pipeline; it is not implemented yet and
`eval/run.py` exits with a clear error if you pass it.

### LangSmith traces and how scores connect back to cases

`eval/langsmith/run_experiment.py` runs the 60 scenarios through
`langsmith.evaluate()` against the `market-research-golden` dataset (must
exist first — see below) rather than a bespoke Python loop. Concretely, per
scenario execution:

- **One trace per case** — `evaluate()` traces the `target()` call for each
  dataset example as a single root run, tagged with that example's
  `scenario_id`/`case_type`/`difficulty` metadata.
- **Child runs are retained**: Pinecone `upsert`/`query` and the embedding
  calls are `@traceable` tool spans (they aren't LangChain `Runnable`s, so
  they wouldn't otherwise nest), and every `ChatOpenAI` call (extraction,
  every judge) shows up as an `llm` child run with real token usage
  (`AnalysisVerificationAgent` captures this via `include_raw=True`).
  Latency, inputs, and outputs are visible on every run without extra code —
  that's what LangSmith traces are.
- **Each judge/metric is its own evaluator function** (`make_evaluators` in
  `run_experiment.py`) — one per metric family (retrieval, red flags,
  conflicts, coverage, faithfulness, abstention, freshness, cost, partial
  failure, latency). Every evaluator call becomes its own small trace *and*
  a feedback score attached back to that example's run — this is what lets
  the LangSmith UI show, for any one case, exactly which metrics passed or
  failed, and what lets you group/filter the whole experiment by
  `case_type` to find a dominant failure mode (e.g. "every CONFLICT scenario
  is failing `conflict_resolution`") and see its latency/token cost
  alongside it.
- **Errors are visible, not swallowed.** A genuinely unexpected exception
  (a real API failure, a bug) propagates out of `target`/an evaluator;
  `evaluate()`'s default `error_handling="log"` marks that run as errored in
  LangSmith and moves on to the next example — it does not silently turn
  into a passing trace. The one *deliberately* simulated failure (MR-059's
  `fail_competitor`) is modeled as a normal-but-partial execution — that
  competitor's branch is skipped, not raised, exactly like the real
  partial-failure-tolerant graph. MR-060's `inject_latency_seconds` is a
  real `time.sleep()` inside `target()`, so the latency it contributes to
  the overall p95 reflects an actually-slow execution rather than a
  synthetic number bolted on afterward.

Aggregate metrics for the release gate/report are reduced directly from the
same evaluator scores (`eval.langsmith.run_experiment.reduce_results`) — no
second round-trip to LangSmith is needed; the scores that became feedback
are read straight off `evaluate()`'s result iterator.

### Running it

```bash
uv run python -m eval.langsmith.create_golden_dataset   # once, or after a scenario change
uv run python -m eval.run --mode frozen --repetitions 1
uv run python -m eval.run --mode frozen --repetitions 3
uv run python -m eval.run --dataset-version gold-v1 --evidence-version evidence-v1 --top-k 5 --repetitions 3
```

Requires `OPENAI_API_KEY`, `PINECONE_API_KEY`, and `LANGCHAIN_API_KEY` (all
real) — `LANGCHAIN_TRACING_V2` does not need to be set for this to work, `evaluate()`
traces independently of that flag. `eval/run.py` exits early with a clear
message if the `market-research-golden` LangSmith dataset doesn't exist yet.
`--repetitions` maps directly to LangSmith's own `num_repetitions` (each
repetition is a separate traced run per example, visible individually in the
UI) — this matters because p95/p99 latency and any judge-score variance are
only meaningful across repeated runs (a single execution's "p95" is just its
max):

- **1 repetition (60x1)** — day-to-day dev loop after a prompt/retrieval
  tweak; fast, cheap, latency percentiles are not meaningful yet.
- **3 repetitions (60x3)** — release-candidate check before a PR/merge that
  touches the Analysis Agent, its prompts, or retrieval.
- **5 repetitions (60x5)** — major release / before a production deploy;
  the most stable read on percentiles and judge-score variance.

`eval/run.py` prints the full report (see below) and exits non-zero when the
release gate's `status == "FAIL"` — nothing wires this into CI yet, but the
exit code is there for when something does.

### Creating/refreshing the LangSmith datasets

```bash
uv run python -m eval.langsmith.create_golden_dataset      # market-research-golden, tagged gold_version
uv run python -m eval.langsmith.create_evidence_dataset    # market-research-evidence, tagged evidence_version
```

Both are idempotent (safe to re-run): each only inserts examples whose
`scenario_id`/`evidence_id` isn't already present in the dataset.

### Comparing two experiments

```bash
uv run python -m eval.langsmith.compare_experiments --baseline-json baseline_metrics.json --candidate-json candidate_metrics.json
uv run python -m eval.langsmith.compare_experiments --baseline-experiment <name> --candidate-experiment <name>
```

Prints a per-metric Baseline / Candidate / Delta table and flags any
**regression** — candidate worse than baseline — accounting for whether the
metric is higher-is-better or lower-is-better (reusing the same flags
`eval.evaluators.release_gate` uses, so "worse" always means the same thing
in both places).

### Metrics and release-gate thresholds

All required/preferred thresholds live in
`eval.schemas.eval_models.ReleaseGateThresholds`; PASS/WARNING/FAIL per
metric is decided by `eval.evaluators.release_gate.evaluate_release_gate`.

| Metric | What it measures | Required | Preferred |
|---|---|---|---|
| `critical_red_flag_recall` | Fraction of `is_critical` gold red flags the agent identified (semantic match via `judges/red_flag_judge.py`). **Below required is always a hard release FAIL**, regardless of every other metric. | 1.00 | — |
| `red_flag_recall` | Same, across all gold red flags. | 0.90 | 0.95 |
| `red_flag_precision` | Correct agent red flags / all agent red flags — penalizes over-flagging. | — (reported, not gated) | — |
| `retrieval_precision_at_5` | Exact-ID Precision@5 against `relevant_evidence_ids`. | 0.70 | 0.80 |
| `retrieval_recall_at_5` | Exact-ID Recall@5 against `relevant_evidence_ids`. | 0.85 | 0.90 |
| `ground_truth_coverage` | Fraction of `gold_facts` semantically recovered (`judges/coverage_judge.py`). | 0.85 | 0.90 |
| `conflict_resolution` | Mean normalized 0-4 conflict-handling rubric score (`judges/conflict_judge.py`). | 0.90 | 0.95 |
| `faithfulness` | Mean normalized 0-4 evidence-faithfulness rubric score (`judges/faithfulness_judge.py`). | 0.90 | 0.95 |
| `unsupported_claim_rate` | Unsupported material claims / total material claims (lower is better). | ≤0.05 | ≤0.02 |
| `cost_projection_error` | `abs(projected - actual) / actual` cost error (lower is better). | ≤0.20 | ≤0.10 |
| `p95_latency_seconds` | p95 wall-clock latency across all scenario executions (lower is better; needs ≥3 repetitions to be meaningful). | ≤60s | ≤45s |
| `partial_failure_correctness` | Resilience scenarios: was a simulated branch failure correctly isolated with no fabricated facts. | 1.00 | — |
| `abstention_accuracy` | Fraction of MISSING_INFO scenarios scored the maximum 2/2 on the abstention rubric (`judges/abstention_judge.py`) — reported alongside the gate metrics above. | — (reported, not yet in `ReleaseGateThresholds`) | — |
| `freshness_accuracy` | Mean normalized 0-3 temporal/freshness rubric score (`judges/freshness_judge.py`) — reported alongside the gate metrics above. | — (reported, not yet in `ReleaseGateThresholds`) | — |

### Adding a new Golden scenario

1. Add the scenario to `eval/datasets/generate_golden_dataset.py` (owned by
   the dataset-generation workstream) — a new `GoldenScenario` with a fresh,
   sequential `scenario_id` (e.g. `MR-061`) and an appropriate `case_type`.
2. Any evidence the scenario's `reference_outputs` refer to
   (`relevant_evidence_ids`, `required_evidence_ids`, a `GoldRedFlag`'s
   `expected_evidence_ids`, a `GoldConflict`'s `evidence_ids_a`/`_b`, a
   `GoldFact`'s `evidence_ids`) must already exist as an `EvidenceRecord` in
   `eval/datasets/frozen_evidence.jsonl` with a matching `evidence_id` and a
   `company` field equal to one of the scenario's `inputs.competitors` — the
   frozen-mode runner only seeds evidence whose `company` matches the
   scenario's target company/competitors into Pinecone, so an evidence_id
   referenced but not present under the right company will simply never be
   retrievable.
3. Re-run `eval/datasets/generate_golden_dataset.py` to regenerate both
   `.jsonl` files, then re-run its validation test (see the file under
   `eval/tests/`/`eval/datasets/` that checks scenario/evidence consistency,
   e.g. that every referenced `evidence_id` actually exists and every
   `content_sha256` matches) to confirm the new scenario is internally
   consistent before it's used for a release gate.
4. If the new scenario is meant to affect a metric's gate threshold, update
   `ReleaseGateThresholds` in `eval/schemas/eval_models.py` and this table.
5. Re-run `uv run python -m eval.langsmith.create_golden_dataset` (and
   `create_evidence_dataset` if new evidence was added) to push the update
   to LangSmith, bumping `gold_version`/`evidence_version` if the change is
   significant enough to want to distinguish old experiment runs from new
   ones.
