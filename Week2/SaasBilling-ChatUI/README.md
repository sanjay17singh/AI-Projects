# SaaS Billing & Subscription Support Bot

A support-chat MVP that combines hybrid retrieval (Pinecone dense + in-memory BM25) with
confidence-based escalation: the bot refuses to guess, and escalates to a human specialist
whenever it isn't confident or a query involves real money. See [`Document/architecture.md`](Document/architecture.md)
for the full pipeline design and escalation logic.

## Prerequisites

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/) — this project uses `uv` exclusively for environment and
  dependency management. No pip/venv/poetry/conda.
- API keys: OpenAI, Pinecone, Mem0 Platform, and (optional but recommended) LangSmith.

## Setup

```bash
uv sync                         # install all dependencies into .venv
cp .env.example .env            # then fill in your API keys
```

## 1. Ingest the knowledge base

Chunks and embeds `data/tickets.json`, `data/faqs.json`, and `data/pricing_docs/*.md`, then
upserts them into a Pinecone dense index (created automatically if it doesn't exist yet).

```bash
uv run python src/ingest.py
```

Safe to re-run — upserts use deterministic ids, so it won't duplicate vectors.

## 2. Launch the app

```bash
uv run streamlit run app.py
```

Chat as a customer. Each reply shows a plain-language answer (or a "connecting you to a
specialist" escalation message), a source badge, and a category badge. Expand "How I got this
answer" on any message to see the retrieved sources, confidence score, and escalation reasoning
— that's the debug/agent view, collapsed by default.

The sidebar lets you set a `customer_id` (so Mem0 memory persists across sessions for that
customer) and reset the conversation.

## 3. Run the evaluation harness

Runs the 20-query test set in `eval/test_queries.json` through the pipeline, once with Mem0
memory enabled and once without, and reports First-Contact Resolution rate, escalation
precision/recall, and possible-hallucination flags.

```bash
uv run python eval/run_eval.py
```

Writes `eval/results_report.md`.

## Project layout

```
Document/       architecture write-up + diagram
data/           synthetic knowledge base (tickets, FAQs, pricing docs)
src/            ingest, retrieval, confidence, memory, graph, schemas
eval/           test queries + eval harness + generated report
app.py          Streamlit UI
```

## Notes

- All escalation thresholds and the $100 money-moving rule live in `src/confidence.py`.
- `src/memory.py` degrades to "no memory available" on any Mem0 failure rather than blocking a
  response; toggle `memory.MEMORY_ENABLED` to disable it entirely (used by the eval harness).
- LangSmith tracing is automatic once `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY` are
  set in `.env` — no code changes needed.
