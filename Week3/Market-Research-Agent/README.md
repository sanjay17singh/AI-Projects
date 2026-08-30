# Market Research Agent

A multi-agent competitor research application for small enterprises: discovers
a company's competitors, gathers current web and news evidence, extracts
structured competitive intelligence, verifies claims against sources, and
generates a cited competitor analysis briefing exportable as Markdown, CSV, or
PDF.

Four agents, orchestrated by two deterministic LangGraph graphs:

1. **Orchestrator** — bounded research plan, budget gating, retries, partial-
   failure resilience, final compilation. Routing (retries/budget/coverage) is
   plain Python, never an LLM decision — see `app/graphs/edges.py`.
2. **Competitor Discovery Agent** — finds 5 candidate competitors via the
   You.com Search API, scores and classifies them (direct/indirect/emerging).
3. **Web Research Agent** — one instance per approved competitor; gathers
   pricing, features, positioning, announcements, and recent news; chunks and
   embeds evidence into Pinecone.
4. **Analysis and Verification Agent** — retrieves evidence per category,
   extracts evidence-backed claims, separates fact from inference, preserves
   conflicting evidence, computes a deterministic coverage score.

**Full setup instructions are in [docs/SETUP.md](docs/SETUP.md)** — env vars,
getting API keys, running Postgres natively (no Docker, by design — see
SETUP.md), migrations, and running the app and tests. A short architecture
overview is in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), and a full
project overview — vision, users, use cases, design decisions, and what's
been validated against live provider accounts — is in
[docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md).

## Quickstart

```bash
uv sync
cp .env.example .env   # fill in OPENAI_API_KEY, YOUCOM_API_KEY, PINECONE_API_KEY
scripts/create_local_db.sh
uv run alembic upgrade head
uv run uvicorn app.api.main:app --reload --port 8000   # terminal 1
uv run streamlit run app/streamlit_app/streamlit_app.py # terminal 2
```

## Tests

```bash
uv run pytest -v
```

25 scenarios, zero live credentials required by default (2 of them opt into a
real Postgres if `TEST_DATABASE_URL` is set — see SETUP.md). LLM-quality evals
(needs real credentials, not run by default) live in `eval/` — see
[eval/README.md](eval/README.md).
