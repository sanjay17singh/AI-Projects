# Setup

## Prerequisites

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/) for dependency management — every command
  in this doc runs through `uv run` so it always uses the project's `.venv`.
- A local Postgres server (e.g. `brew install postgresql@16 && brew services start postgresql@16`
  on macOS, or your distro's package for Linux). **No Docker is used anywhere
  in this project, by explicit choice** — see "Why no Docker" below.

## 1. Get API keys

| Service | Used for | Get it at |
|---|---|---|
| OpenAI | LLM calls (structured output) + embeddings | platform.openai.com/api-keys |
| You.com | Web + news search (Discovery and Web Research agents) | you.com — Search API dashboard |
| Pinecone | Vector store for research evidence | app.pinecone.io — API Keys |
| Serper.dev | Optional second web/news search provider (Web Research agent) | serper.dev — Dashboard → API Key |
| LangSmith | Optional — dev tracing/eval; app runs fine without it | smith.langchain.com — Settings → API Keys |

The app **requires** real OpenAI/You.com/Pinecone keys to actually run —
there is no mock/offline mode. Only the test suite (`tests/`) works without
any of them. Serper.dev is optional and off by default (see below).

## 2. Clone and configure

```bash
uv sync                    # creates .venv, installs from pyproject.toml/uv.lock
cp .env.example .env
```

Fill in `.env`:

- `OPENAI_API_KEY`, `YOUCOM_API_KEY`, `PINECONE_API_KEY` — required.
- `OPENAI_MODEL` / `OPENAI_MODEL_FAST` — both default to `gpt-4o-mini`.
  `OPENAI_MODEL_FAST` backs the simpler, higher-volume steps (query
  generation, discovery scoring); `OPENAI_MODEL` backs claim extraction/
  verification, where judgment quality matters most. You can point
  `OPENAI_MODEL` at a stronger model later without touching anything else.
- `OPENAI_EMBEDDING_MODEL` — defaults to `text-embedding-3-small` (1536-dim;
  matches the Pinecone index config below — changing it requires a new index).
- `LANGCHAIN_API_KEY` / `LANGCHAIN_TRACING_V2` — optional; leave blank/false
  to skip tracing entirely, the app works fine either way.
- `DEFAULT_BUDGET_USD_LIMIT`, `COVERAGE_THRESHOLD`, `MAX_RETRIES_PER_COMPETITOR`,
  `MAX_GAP_RETRIES` — tune the orchestrator's deterministic gates; the
  shipped defaults (5.00, 0.6, 2, 3) are reasonable starting points.
- `SERPER_ENABLED` / `SERPER_API_KEY` / `SERPER_BASE_URL` — optional second
  search provider for the Web Research agent, used **alongside** You.com
  (not instead of it) so each competitor's evidence is drawn from two
  independent indexes rather than just one. Off by default
  (`SERPER_ENABLED=false`) — the app runs fine with You.com alone. To turn
  it on: get an API key from serper.dev, set `SERPER_API_KEY`, and set
  `SERPER_ENABLED=true`. `SERPER_BASE_URL` defaults to
  `https://google.serper.dev` and normally doesn't need to change. Note the
  toggle is deliberately explicit and separate from just having a key
  configured — setting `SERPER_API_KEY` without `SERPER_ENABLED=true` leaves
  Serper off.

## 3. Local Postgres (no Docker)

```bash
scripts/create_local_db.sh                      # creates `competitor_research`, enables pgcrypto
scripts/create_local_db.sh competitor_research_test   # optional, for TEST_DATABASE_URL below
```

`DATABASE_URL` in `.env.example`/`.env` already points at
`postgresql+psycopg://localhost:5432/competitor_research` — adjust host/port/
user if your local Postgres is configured differently.

Run migrations:

```bash
uv run alembic upgrade head
```

This creates the audit-trail schema (`runs`, `discovery_candidates`,
`research_evidence`, `competitor_profiles`, `analysis_claims`, `run_costs`,
`run_events`, `briefings`, etc.) plus, on first app startup, the LangGraph
checkpoint tables (`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`) —
those are created by the app itself (`PostgresSaver.setup()`), not Alembic,
since they belong to LangGraph rather than this project's own schema.

## 4. Run it

```bash
uv run uvicorn app.api.main:app --reload --port 8000
```

In a second terminal:

```bash
uv run streamlit run app/streamlit_app/streamlit_app.py
```

Open the Streamlit URL it prints (typically `http://localhost:8501`). The
Streamlit app talks to the backend via `BACKEND_BASE_URL` (defaults to
`http://localhost:8000`).

`GET http://localhost:8000/healthz` checks DB connectivity only — it works
even before your API keys are configured, so it's a good first sanity check.

## 5. Run the tests

```bash
uv run pytest -v
```

All 25 scenarios run by default with **zero live credentials** — external
calls (OpenAI, You.com, Pinecone) are replaced with fakes/fixtures at the
client-adapter boundary. Two of them (`test_t17...postgres`, `test_t18...`)
additionally run against a real Postgres if `TEST_DATABASE_URL` is set in
`.env` (pointing at the second database created above), and skip cleanly
otherwise. Test results are logged on every run (`pyproject.toml` sets
`addopts = "-ra --log-cli-level=INFO"`).

## 6. LLM-quality evals (optional, separate from tests)

`eval/` is a different thing from `tests/` — it scores actual LLM output
quality against real credentials and is never run automatically. See
[eval/README.md](../eval/README.md).

## Updating provider pricing

`app/services/cost_service.py`'s `PRICE_TABLE` holds the per-unit USD prices
used to project and track run cost. It's a plain constant, not env-driven —
update it there when OpenAI/You.com/Pinecone pricing changes.

## Why no Docker

This project deliberately ships without Dockerfiles or docker-compose, by
explicit choice made during design — everything above runs natively. If you
want to containerize it later: two images (backend running
`uvicorn app.api.main:app`, frontend running
`streamlit run app/streamlit_app/streamlit_app.py`), a `postgres:16` container
for the database, and an entrypoint that runs `alembic upgrade head` before
starting the backend. Nothing in the application code assumes a native
environment — this is a packaging choice, not an architectural one.

## Troubleshooting

- **`/healthz` returns `"degraded"`**: Postgres isn't reachable at
  `DATABASE_URL` — check it's running and the database exists
  (`scripts/create_local_db.sh`).
- **Backend logs "Could not ensure Pinecone index at startup"**: expected
  until `PINECONE_API_KEY` is set to a real key; the app still starts (you'll
  just get errors from any endpoint that actually needs Pinecone until it's
  configured).
- **Backend logs "Could not set up the LangGraph Postgres checkpointer"**:
  same as above, but for `DATABASE_URL` — budget-approval resume won't work
  until Postgres is reachable, but discovery (which doesn't need the
  checkpointer) still works.
- **Pinecone dimension mismatch on an existing index**: if you change
  `OPENAI_EMBEDDING_MODEL` to one with a different dimension, you need a new
  Pinecone index (change `PINECONE_INDEX_NAME`) — Pinecone can't resize an
  existing index in place.
