# Architecture

Brief reference — read the code for anything this doesn't cover; nothing
here should ever be more authoritative than `app/`.

## Flow

```
Streamlit (app/streamlit_app/)
  → FastAPI (app/api/) — creates a run, schedules a graph as a BackgroundTask
    → Discovery graph (app/graphs/discovery_graph.py)
        normalize_request → generate_search_queries → call_youcom_search
          → score_and_classify_candidates → persist_candidates
    ⋯ human picks 3 competitors over POST .../selection ⋯
    → Research+Analysis graph (app/graphs/research_analysis_graph.py)
        plan_research → [budget gate] → fan-out web_research_node (×3)
          → research_join_node → fan-out analysis_node (×successful)
          → analysis_join_node → [coverage gate] → gap_research_node (loop)
          → compile_briefing → finalize_run
  → Postgres (audit trail) + Pinecone (evidence vectors)
```

Two separate graph runs, not one graph with `interrupt()` — human competitor
approval is a REST boundary between them. The second graph uses a Postgres
`PostgresSaver` checkpointer solely so a mid-run "approve more budget" pause
(`request_budget_approval` node) can survive an HTTP request boundary; a
later `POST .../approve-budget` call resumes the same LangGraph thread
(`thread_id = run_id`).

## Deterministic routing

Every conditional-edge function lives in `app/graphs/edges.py` as a plain
function of state fields — no LLM call anywhere in that file. Counters
(`retry_count`, `retry_counts`, `gap_retry_counts`) are incremented by
dedicated nodes (`record_search_retry_node`, `research_join_node`,
`analysis_join_node`), never by the edges themselves, so routing logic stays
pure and independently testable (see `tests/graph/`).

## Layering

- `app/clients/*` — the only files that import `openai`/`pinecone` or call
  You.com over HTTP. This is the seam every test replaces with a fake.
- `app/agents/*` — LLM + tool logic. No LangGraph wiring.
- `app/graphs/*` — state (`app/schemas/graph_state.py`), nodes, edges, and the
  two compiled `StateGraph`s.
- `app/services/*` — the only files that touch a DB session. Agents and graph
  nodes call services; they never `session.add()` directly.
- `app/export/*` — pure Python templating over verified `CompetitorProfile`
  objects. No LLM call in the compile step — that absence is what
  structurally guarantees the briefing never states a fact absent from
  verified agent output.

## Data model

- **Postgres** (`app/db/models.py`, `migrations/versions/0001_initial_schema.py`):
  `workspaces`, `runs`, `discovery_candidates`, `competitor_selections`,
  `research_evidence` (source-level audit trail — URL, hash, fetched_at,
  `embedding_status`), `competitor_profiles`, `analysis_claims`
  (claim-level audit trail — `evidence_ids` pointing back to
  `research_evidence.id`), `run_costs`, `run_events`, `briefings`.
  Chunk-level evidence *text* lives only in Pinecone, not Postgres — a
  deliberate tradeoff (see the plan's decision log) trading independent
  recoverability for a simpler schema.
- **Pinecone**: one index (`competitor-research`), one namespace per
  workspace, vector id `f"{evidence_id}_{chunk_index}"`. Every query filters
  on `run_id` + `competitor_id` (+ `category`, + a date range for news), so
  sharing a namespace across runs is safe.

## Agents

1. **Discovery** (`app/agents/discovery_agent.py`) — `OPENAI_MODEL_FAST` for
   query generation and candidate scoring; You.com for search; never
   auto-approves the final three.
2. **Web Research** (`app/agents/web_research_agent.py`) — one instance per
   competitor; dedupes by canonical URL + content hash
   (`app/services/evidence_service.py`); chunks (`app/utils/text_splitting.py`)
   and embeds into Pinecone; never raises out of a graph node.
3. **Analysis and Verification** (`app/agents/analysis_agent.py`) —
   `OPENAI_MODEL` (the stronger tier); 11 separate retrieval queries per
   competitor (10 coverage categories + company description); every non-
   "Not publicly available" claim must carry `evidence_ids`
   (`app/schemas/analysis.py`'s `ClaimField` validator); coverage score is
   computed deterministically in Python
   (`app/services/analysis_service.compute_coverage_score`), never
   LLM-reported, because it drives the coverage-check edge.
4. Verification is folded into the Analysis agent for this MVP — no separate
   fifth agent.

## Prompt-injection resistance

`app/prompts/injection_guard.py` wraps every piece of raw scraped content
that reaches an LLM in `<retrieved_web_content>` tags, paired with a fixed
system-prompt clause telling the model to treat that tag's contents strictly
as data, never as instructions. Applied identically in
`web_research_prompts.py` and `analysis_prompts.py`.
