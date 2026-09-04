# AgentGate

A CI/CD security and evaluation gate for AI agents. AgentGate takes a
proposed change to an agent (prompt, model, tool, policy, or retrieval
change), runs it through a mandatory catalog of benign, adversarial, and
resilience scenarios against a sandboxed copy of the agent, applies
deterministic security/authorization rules before any LLM judgment, pauses
for required human approvals, and produces an auditable release
recommendation: `APPROVE`, `APPROVE_WITH_CONDITIONS`, `BLOCK`, or
`INCONCLUSIVE`.

For the full narrative — problem statement, architecture diagrams, the
primary demonstration walked through step by step, and what's deliberately
out of scope — see [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md).

## Architecture at a glance

- **Orchestration:** LangGraph `StateGraph` with typed state
  (`app/schemas/state.py`), Postgres-backed checkpointing, and
  `interrupt()`/`Command(resume=...)` for every human-in-the-loop pause.
  Only `app/agents/orchestrator.py` decides where the graph goes next. The
  checkpoint serializer explicitly allow-lists every Pydantic type that can
  appear in state (`app/db/checkpointer.py`) rather than permitting arbitrary
  types with a warning — an unregistered type is blocked from
  reconstruction, not silently deserialized.
- **9 named agents:** Orchestrator, Change Analysis, Scenario Design, Sandbox
  Execution, Policy Evaluation, Guardrail Recommendation, Regression Test,
  Report Generation, and the Target Support Agent under test (`app/agents/`).
- **Deterministic-first policy evaluation:** hard security/authorization
  rules (`app/policy/deterministic_rules.py`) run before any LLM judgment,
  and an LLM verdict can never override a deterministic failure.
- **Postgres is the system of record** for runs, scenarios, executions,
  findings, evidence, guardrails, human reviews/decisions, release decisions,
  regression tests, and audit events — all idempotent on creation. LangGraph
  checkpoint tables are a physically separate schema (`langgraph-checkpoint-postgres`'s
  own tables), never joined against the audit tables.
- **Pinecone** is used only for semantic retrieval (policies, prior failures,
  regression descriptions, sanitized evidence) and degrades gracefully to the
  local scenario catalog if unavailable — the run and report explicitly
  record degraded coverage rather than silently claiming full coverage.
- **40 version-controlled scenarios** under `scenarios/{adversarial,benign,resilience}/`,
  schema-validated and count-validated by `tests/scenarios/test_catalog_validation.py`.

## Prerequisites

- Python 3.12
- [`uv`](https://docs.astral.sh/uv/)
- A local or managed PostgreSQL instance
- (Optional) OpenAI API key, Pinecone API key, LangSmith API key — the app
  runs in a fully functional degraded/fake mode without any of these (see
  **Running without credentials** below).

## Setup

```bash
# 1. Install dependencies
uv sync

# 2. Create the databases (adjust for your Postgres setup)
createdb agentgate
createdb agentgate_test   # used by the test suite

# 3. Configure environment
cp .env.example .env
# edit .env — at minimum set DATABASE_URL; OPENAI_API_KEY/PINECONE_API_KEY/
# LANGSMITH_API_KEY are all optional (see below)

# 4. Run migrations (business/audit schema)
uv run alembic upgrade head

# 5. Set up the LangGraph checkpoint tables (separate schema, idempotent)
uv run python scripts/setup_checkpointer.py
```

## Running

```bash
# API
uv run uvicorn app.api.main:app --reload

# UI (in a separate terminal; defaults to talking to the API at localhost:8000,
# override with AGENTGATE_API_URL)
uv run streamlit run app/ui/main.py

# Tests
uv run pytest
```

The Streamlit UI has six pages: **Dashboard**, **New evaluation**, **Run
details**, **Human review**, **Final report**, and **Scenario library**.

## Running the primary demonstration

```bash
uv run python scripts/run_demo.py
```

This reproduces AgentGate's primary demonstration end-to-end: a malicious
instruction embedded in a retrieved knowledge-base document tricks the
*vulnerable* Target Support Agent into attempting an unauthorized $500
refund; AgentGate's deterministic policy layer flags it as a finding; a
guardrail is proposed; a (simulated, in the console) human approves it;
LangGraph resumes from the Postgres checkpoint; the *guarded* agent is
re-verified clean; the failure becomes a permanent regression test; a report
is generated; and a final human release decision is required because the
change touches refunds and customer data.

**Running without credentials:** if `OPENAI_API_KEY` isn't set, the script
runs in *fake mode* — the LLM judgments and the Target Support Agent's
tool-calling loop are replaced with deterministic stand-ins
(`app/demo/fakes.py`) that reproduce this exact narrative, so the graph's
control flow, checkpointing, interrupts, deterministic policy engine, and
Postgres persistence are all still exercised for real. Set a real
`OPENAI_API_KEY` in `.env` to run the actual Target Support Agent and
LLM-calling agents instead — no code changes needed.

You can inspect the resulting run afterward via the Streamlit UI or:

```bash
curl http://localhost:8000/evaluations/<run_id>/report
```

## Testing

```bash
uv run pytest                    # full suite (unit, integration, scenario-validation, workflow)
uv run pytest tests/scenarios    # just the 40-scenario catalog validation
uv run pytest tests/workflow     # full graph runs against a real Postgres test DB, fully faked LLM
uv run pytest -m external        # tests requiring live OpenAI/Pinecone credentials (none currently marked; opt-in only)
```

Integration and workflow tests run against a real local `agentgate_test`
Postgres database (never mocked) and fully fake the OpenAI/Target-Support-Agent
layer (`app/demo/fakes.py`) — this is deliberate: the properties worth
proving for real are Postgres persistence, idempotency, checkpoint
resume, and the deterministic policy engine, none of which benefit from a
live LLM call, and this keeps the suite fast and hermetic.

## FastAPI endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/evaluations` | Start an evaluation (requires `Idempotency-Key` header) |
| `GET` | `/evaluations` | List evaluation runs |
| `GET` | `/evaluations/{run_id}` | Run status summary |
| `GET` | `/evaluations/{run_id}/state` | Full graph state (executions, findings, guardrails, decisions, pending review) |
| `GET` | `/evaluations/{run_id}/scenarios` | Scenario execution results |
| `GET` | `/evaluations/{run_id}/findings` | Findings |
| `GET` | `/evaluations/{run_id}/report` | Final evaluation report (404 until Report Generation has run) |
| `GET` | `/human-reviews/pending` | Pending human review queue |
| `POST` | `/human-decisions` | Submit a human decision (idempotent) |
| `GET` | `/health` | Postgres/Pinecone/OpenAI/LangSmith status |

## Environment variables

See `.env.example`. All configuration flows through `app/config.py`
(`Settings`) — no other module reads `os.environ` directly.

## Repository layout

```
app/
  agents/         the 9 named agents + Target Support Agent (vulnerable/guarded)
  api/            FastAPI app and routes
  audit/          audit event logging + secret/PII redaction
  db/             SQLAlchemy models, Alembic-migrated schema, checkpointer setup, repository (idempotent writes)
  demo/           deterministic fakes shared by scripts/run_demo.py and the workflow test suite
  graph/          LangGraph StateGraph assembly + run/resume orchestration
  policy/         deterministic security/authorization rules (zero-LLM assertion engine)
  retrieval/      Pinecone client + graceful-degradation fallback
  schemas/        Pydantic models + the typed LangGraph state
  tracing/        optional, privacy-redacting LangSmith integration
  ui/             Streamlit app (6 pages) + its API client
migrations/       Alembic migrations (business/audit schema only)
prompts/          version-controlled agent system prompts
scenarios/        the 40 mandatory evaluation scenarios (YAML) + schema/loader
scripts/          setup + demo scripts
tests/            unit, integration, scenario-validation, and workflow tests
docs/post-mvp.md  documented, deliberately out-of-scope capabilities
```

## Known MVP limitations

- **Single-tenant in practice.** `tenant_id` exists on the change/Pinecone
  namespace, but there's no auth, no per-user identity, and no enforced
  cross-tenant isolation. See `docs/post-mvp.md`.
- **No authentication** on the FastAPI or Streamlit layers — anyone who can
  reach the API can submit evaluations and human decisions. Fine for a local
  MVP demo, not for a shared deployment.
- **Regression-test promotion is recorded, not enforced.** Sensitive/high-risk
  regression tests get a `regression_promotion` human-review request, but a
  run isn't blocked on that promotion decision — it's tracked in the Human
  Review queue independently.
- **Scenario Design's category selection is deterministic, not LLM-driven**
  (all adversarial scenarios are always in scope; benign scenarios are
  filtered by the Change Analysis Agent's reported coverage categories).
  This was a deliberate choice for reproducibility, not a shortcut — see the
  docstring in `app/agents/scenario_design.py`.
- **No real embedding/vector content is pre-loaded into Pinecone.** The
  client and degradation path are fully implemented and tested, but seeding
  the index with actual policy/support documentation is left to the
  operator (`PineconeRetriever.upsert_documents`).
- Post-MVP capabilities (A2A adapter, cross-run trend/learning layer, full
  multi-tenant/multi-user support) are documented but not built — see
  `docs/post-mvp.md`.
