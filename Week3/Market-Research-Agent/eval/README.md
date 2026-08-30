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
