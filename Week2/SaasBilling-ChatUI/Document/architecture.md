# Architecture — SaaS Billing Support Bot

## Core principle

The bot refuses to guess. Every answer is grounded in retrieved sources and gated by a
confidence score; when confidence is low, or a query involves real money, the pipeline
escalates to a human specialist instead of surfacing an unreliable answer.

## Pipeline stages

```
Customer Query + Memory Lookup (Mem0)
        ↓
Intent Classification (category tagging)
        ↓
Hybrid Retrieval (Pinecone dense + in-memory BM25, fused via RRF)
        ↓
Generation with Confidence Scoring (structured output)
        ↓
LangGraph Decision — Answer vs. Escalate
        ↓
Escalation Handoff (human agent) / Answer Delivered
```

Implemented as a linear LangGraph `StateGraph` (`src/graph.py`) with six nodes:
`load_memory → classify → retrieve → generate → score_and_decide → save_memory`. The graph is
deliberately linear and deterministic — no `AgentExecutor`, no one-shot `RetrievalQA`. Control
flow is explicit code, not something an LLM improvises, because the escalation logic this
project depends on has to be auditable.

## Tech stack and why

| Layer | Choice | Why |
|---|---|---|
| Embeddings | OpenAI `text-embedding-3-small` | Cheap, fast, good quality for a small synthetic KB. |
| Generation | OpenAI `gpt-4o-mini`, structured output | Cheap enough to run classification + generation on every turn plus a 20-query eval suite; structured output (`with_structured_output`) enforces the confidence/escalation schema instead of parsing free text. |
| Vector store | Pinecone (dense only) | Managed, no infra to run; used strictly as the dense vector store. |
| Keyword search | BM25 (`rank_bm25`, in-memory) | Built directly from the source knowledge base at process start — no separate persistence layer needed for a corpus this small (~65 chunks). |
| Hybrid fusion | LangChain `EnsembleRetriever` (RRF, weights 0.5/0.5) | Combines the Pinecone dense retriever and the BM25 retriever via Reciprocal Rank Fusion. This also stands in for a separate cross-encoder/Cohere rerank stage: the fused RRF rank is a materially better confidence signal than raw cosine or BM25 scores taken alone, which is the property a rerank step is meant to provide. |
| Control flow | LangGraph `StateGraph` | Explicit, typed state machine — classify/retrieve/generate/decide are separate, auditable nodes rather than one LLM call improvising the whole flow. |
| Components | LangChain | Supplies the wrappers (`ChatOpenAI`, `OpenAIEmbeddings`, `PineconeVectorStore`, `RecursiveCharacterTextSplitter`, structured-output parsing) that LangGraph's nodes call into. |
| Tracing/eval | LangSmith | Every run (classification, retrieval, confidence, escalation decision) is traced automatically once `LANGCHAIN_TRACING_V2` is set — no manual instrumentation. Also the harness for the eval step. |
| Long-term memory | Mem0 Platform | Hosted, so no local vector DB to run just for a small customer-context store. Kept as its own module (`src/memory.py`) so it can be disabled for the eval harness's memory-off pass. |
| Package management | `uv` | `uv sync` / `uv run` exclusively — no pip/venv/poetry/conda anywhere in setup or docs. |

## Retrieval detail

Why Pinecone dense-only + separate in-memory BM25, instead of a single Pinecone hybrid
(dense+sparse) index: it keeps the corpus for keyword search exactly the source knowledge base
(no separate sparse-vector encoding step to keep in sync), and lets the fusion weighting be
tuned independently of Pinecone's index configuration. Both retrievers see the same chunks —
`RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)` over tickets, FAQs, and
pricing docs, each chunk tagged with `source_id`, `source_type` (ticket/faq/pricing_doc), and
`category`. Retrieval can optionally filter the Pinecone side by category once the classifier is
confident about it.

## Confidence & escalation logic (`src/confidence.py`)

The generation node returns a structured `BotResponse`:

```json
{
  "answer": "string or null",
  "citations": ["source_id", "..."],
  "confidence": 0.0,
  "category": "refund | proration | payment_failure | cancellation | upgrade_downgrade | invoice_dispute | general_policy",
  "dollar_amount": 0.0,
  "escalate": true,
  "escalation_reason": "string or null"
}
```

`confidence.decide()` is the single, centralized, deterministic authority over the final
escalate/answer decision — it never trusts the LLM's own `escalate` guess as the last word (it
can only push toward escalation, never override an escalation back to "answer"):

| Category group | Confidence bar | Dollar rule |
|---|---|---|
| `refund`, `proration`, `invoice_dispute` (money-moving) | ≥ 0.90 | Escalate unconditionally if `dollar_amount > $100`, regardless of confidence |
| `general_policy`, `payment_failure`, `cancellation`, `upgrade_downgrade` (informational/process) | ≥ 0.60 | — |

An answer is only ever surfaced to the customer when it clears its category's bar; if
`escalate=True` for any reason, `answer` is redacted to `null` before it reaches the UI, even if
the model produced a non-null answer.

## Memory boundary (Mem0)

Mem0 (`src/memory.py`) is a customer-specific memory store, separate from the retrieval
knowledge base:

- **What's stored**: plan tier, prior issues raised, prior escalations (with category + reason),
  stated preferences — written as short, LLM-summarized notes at the end of each turn, not the
  full transcript.
- **When it's read**: at the start of every query (`load_memory` node), injected as background
  context into both the `classify` and `generate` prompts, and into the final escalation
  decision.
- **The boundary that must never be crossed**: memory can raise the bar for escalation or add
  context, but it can never fabricate facts or serve as a citation source. Both prompts
  explicitly instruct the model that customer context is "background only, never a citation
  source" — the answer must still be grounded in retrieved tickets/FAQs/pricing docs.
- **Escalation override**: if a customer has 2+ prior escalations in the same category
  (`MEMORY_ESCALATION_OVERRIDE_COUNT` in `src/schemas.py`), the pipeline escalates immediately
  regardless of how confident the current turn's retrieval/generation looks — it does not
  re-attempt a bot answer.
- **Failure mode**: any Mem0 error is caught and treated as "no memory available" — it never
  blocks or crashes the response path.
- **Disableable for eval**: `memory.MEMORY_ENABLED` is a module-level flag the eval harness
  toggles to run the 20-query suite both with and without memory, since single-shot queries with
  no history otherwise can't show whether continuity changes escalation accuracy.

## Error handling

Each external call (Pinecone retrieval, OpenAI classification/generation, Mem0 read/write) is
wrapped in `src/graph.py`. A Pinecone or OpenAI failure sets a `system_error` flag on the graph
state; downstream nodes short-circuit, and `score_and_decide` turns it into a forced escalation
(`escalate=True`, `escalation_reason="System error: ..."`) rather than raising into the Streamlit
UI. A Mem0 failure is swallowed inside `memory.py` itself and simply yields no memory context.

## Evaluation approach

`eval/run_eval.py` runs the 20 queries in `eval/test_queries.json` — a mix of clear-cut
informational questions (expected: answer), underspecified/ambiguous questions (expected:
escalate), and money-specific questions over the $100 cap (expected: escalate regardless of
confidence) — through the same `graph.run()` entry point used by the app, twice: once with Mem0
memory disabled (fresh customer per query) and once with it enabled (a single customer id shared
across all 20 queries in order, so prior escalations can accumulate and trigger the memory
override rule).

For each pass it reports:

- **First-Contact Resolution (FCR)** — % of queries the bot correctly answered without
  escalating.
- **Escalation precision/recall** — against each query's expected label.
- **Possible-hallucination flags** — an automated proxy (any surfaced answer with zero
  citations), intended as a starting point for the manual check the spec calls for, not a
  replacement for actually reading each answer against the source documents.

Results are written to `eval/results_report.md`; LangSmith trace links are available per-run
under the `LANGCHAIN_PROJECT` configured in `.env` once tracing is enabled.
