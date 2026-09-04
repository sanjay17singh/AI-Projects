# Post-MVP capabilities

These were discussed and deliberately deferred out of the one-week MVP scope.
Nothing here is implemented — this documents the design intent and what
changing scope would require, per the project's request to track optional
capabilities separately from the build.

## 1. A2A external adapter

**What:** Expose AgentGate as an [A2A](https://github.com/google/A2A)-callable
agent so external orchestrators or other agent ecosystems can submit a change
for evaluation and poll for a verdict via a standard protocol, without
needing to know AgentGate's own REST schema.

**Why deferred:** Not needed for the demo or any explicit MVP requirement,
and the project's spec explicitly excludes A2A for *internal* agent
communication (LangGraph typed state is used instead — see
`app/schemas/state.py` and `app/graph/workflow.py`).

**What it would take:** A thin adapter module (`app/api/a2a.py`) publishing
an Agent Card manifest and translating A2A task-create/task-status calls into
the existing `POST /evaluations` / `GET /evaluations/{id}` endpoints. No
change to the graph, agents, or database — this is purely additive on top of
the existing FastAPI layer. The main open design question is how a
long-running human-in-the-loop pause (which can take hours or days) maps
onto A2A's task lifecycle — as a long-running task the caller polls, or a
separate notification mechanism.

**Explicitly not recommended:** replacing *internal* agent-to-agent
communication (the 9 named agents talking via LangGraph state today) with
A2A. That would break the single-process, single-checkpoint state model the
audit trail and human-in-the-loop resume mechanics depend on, and would
require re-implementing the "deterministic authorization checks can never be
overridden by an LLM" invariant across process boundaries instead of within
one shared state object.

## 2. Trend / learning layer

**What:** A small aggregation layer over the existing Postgres audit history
— e.g. a `tenant_risk_profile` or `guardrail_effectiveness` table, refreshed
after each run — surfacing patterns like "this tenant's changes trigger
cross-customer-access findings 3x more than average" or "guardrail X was
applied on 2026-08-01 and no injection scenario has failed since."

**Why deferred:** Not part of the original 9-agent / 40-scenario / fixed
workflow specification; a genuine enhancement rather than a gap.

**What it would take:** No new infrastructure or dependency — this is purely
a summary view over `findings`, `guardrail_recommendations`, and
`regression_tests`, computed by a scheduled job or on-demand query. The
Change Analysis and Scenario Design Agents could then consult it (e.g. via a
new Pinecone-indexed summary, keeping Pinecone as the semantic layer it
already is) to prioritize scenario coverage for a given tenant based on its
own history, not just the current change's content.

## 3. Full multi-tenant / multi-user support

**What's already in the MVP:** `tenant_id` is present on `ProposedChange` /
`proposed_changes`, and Pinecone namespaces are already tenant-prefixed
(`{PINECONE_NAMESPACE_PREFIX}-{tenant_id}`) — see
`app/retrieval/pinecone_client.py`. There is no authentication, no per-user
identity, and no enforcement that a caller can only see their own tenant's
data; the MVP is effectively single-tenant in practice.

**Why deferred:** Explicitly scoped out during planning — the MVP prioritizes
proving the full evaluation/HITL/audit pipeline over access control.

**What full support would require:**
- `tenant_id` propagated to every table that doesn't already have it
  (`evaluation_runs`, `findings`, `guardrail_recommendations`,
  `human_review_requests`, `regression_tests`, `audit_events`,
  `scenario_executions`), with a repository layer that always filters by it.
- Postgres **Row-Level Security** policies as defense-in-depth beyond
  application-level filtering (`SET app.current_tenant_id` per connection).
- Idempotency keys scoped per tenant: `(tenant_id, idempotency_key)` instead
  of a bare unique key, since two tenants may legitimately reuse a key.
- A `users` table (id, tenant_id, email, role) with `human_decisions.reviewer`
  and `audit_events.actor` becoming real foreign keys instead of free-text
  strings.
- Role-based permissions mapping the 6 human-approval types (budget,
  guardrail, override, release, regression promotion, publish) to who may
  decide them.
- Auth on both interfaces: a per-tenant API key at minimum for the FastAPI
  layer (full OAuth/SSO is a further step beyond that), and a login/tenant
  selection step in Streamlit.
- Pinecone metadata filtering on `tenant_id` in addition to the namespace, as
  belt-and-suspenders against a namespace-routing bug.
- A cross-tenant isolation test suite proving tenant A cannot read tenant B's
  runs, findings, or review queue — including by guessing an ID.
