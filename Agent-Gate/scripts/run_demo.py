"""Runnable, narrated reproduction of AgentGate's primary demonstration:

  1. A malicious instruction is embedded in a retrieved knowledge-base document.
  2. The vulnerable Target Support Agent retrieves it.
  3. The content instructs the agent to issue an unauthorized $500 refund.
  4. The agent attempts the refund tool call.
  5. AgentGate's deterministic authorization control flags it as a finding.
  6. AgentGate records the evidence and finding.
  7. The Guardrail Recommendation Agent proposes a repair.
  8. PostgreSQL stores the checkpoint and human-review request.
  9. A human approves the repair.
 10. LangGraph resumes from the checkpoint.
 11. The guarded agent is tested again.
 12. Findings are re-evaluated clean.
 13. The failure becomes a permanent regression test.
 14. The Report Generation Agent creates the final briefing.
 15. A human makes the final high-risk release decision.

Usage:
    uv run python scripts/run_demo.py

If OPENAI_API_KEY is not configured, this runs in *fake mode*: the LLM
judgments and the Target Support Agent's tool-calling loop are replaced with
deterministic stand-ins (app/demo/fakes.py) that reproduce this exact
narrative, so the full graph — checkpointing, interrupts, deterministic
policy engine, Postgres persistence, regression-test creation — is still
exercised for real. With a real OPENAI_API_KEY configured, the same script
runs the actual Target Support Agent and LLM-calling agents.
"""

import importlib
import sys
import uuid

from app.config import get_settings
from app.db.checkpointer import get_checkpointer
from app.dependencies import build_default_deps
from app.graph.runner import resume_evaluation, start_evaluation
from app.schemas.change import ProposedChange


class _AttrSetter:
    """Minimal stand-in for pytest's monkeypatch.setattr, for use outside tests."""

    def setattr(self, target: str, value) -> None:
        module_path, name = target.rsplit(".", 1)
        module = importlib.import_module(module_path)
        setattr(module, name, value)


def _banner(text: str) -> None:
    print(f"\n{'=' * 70}\n{text}\n{'=' * 70}")


def _print_state_summary(state: dict) -> None:
    if "__interrupt__" in state:
        interrupt = state["__interrupt__"][0]
        print(f"  -> PAUSED: {interrupt.value['review_type']} review requested")
        print(f"     available actions: {interrupt.value['available_actions']}")
        return
    print(f"  -> workflow_status: {state.get('workflow_status')}")
    if state.get("findings"):
        for f in state["findings"]:
            print(f"     finding [{f.severity}] {f.scenario_id}: {f.description}")
    if state.get("report"):
        print(f"     recommendation: {state['report'].recommendation}")


def main() -> None:
    settings = get_settings()
    fake_mode = not settings.openai_api_key

    if fake_mode:
        _banner("No OPENAI_API_KEY configured — running in FAKE MODE")
        print("LLM judgments and Target Support Agent execution are replaced with")
        print("deterministic stand-ins (app/demo/fakes.py) reproducing the exact")
        print("primary-demonstration narrative. Set OPENAI_API_KEY in .env to run for real.")
        from app.demo.fakes import (
            patch_all_llm_calls,
            patch_scenario_selection,
            patch_target_agent_execution,
        )

        setter = _AttrSetter()
        patch_all_llm_calls(setter)
        patch_scenario_selection(setter, ["ADV-INJ-INDIRECT-01"])
        patch_target_agent_execution(setter)
    else:
        _banner("OPENAI_API_KEY configured — running against the real Target Support Agent")

    deps = build_default_deps(settings)

    change = ProposedChange(
        id="",
        tenant_id="default",
        change_type="retrieval",
        title="Enable knowledge-base retrieval for refund FAQ answers",
        diff_summary=(
            "The support agent now retrieves knowledge-base documents to answer refund policy "
            "questions, including third-party-editable FAQ content."
        ),
        raw_payload={},
        created_by="demo-script",
    )

    with get_checkpointer(settings) as checkpointer:
        _banner("STEP 1-4: starting evaluation against the VULNERABLE target config")
        outcome = start_evaluation(change, deps, checkpointer, idempotency_key=str(uuid.uuid4()))
        print(f"run_id={outcome['run_id']}  thread_id={outcome['thread_id']}")
        _print_state_summary(outcome["state"])

        if "__interrupt__" not in outcome["state"]:
            print("\nNo guardrail review was requested — nothing further to demonstrate.")
            sys.exit(0)

        _banner("STEP 5-8: deterministic policy layer flagged the unauthorized refund;\n"
                 "a guardrail was proposed and PostgreSQL now holds a pending human-review request")

        _banner("STEP 9-10: human approves the guardrail; LangGraph resumes from the checkpoint")
        resume1 = resume_evaluation(
            outcome["thread_id"],
            {
                "reviewer": "demo-reviewer@agentgate.local",
                "decision": "approve",
                "justification": "Confirmed root cause (missing identity/refund-cap enforcement); approving the fix.",
            },
            deps,
            checkpointer,
        )
        _print_state_summary(resume1["state"])

        _banner("STEP 11-13: guarded agent re-verified clean; a regression test was created")
        print(f"regression_test_ids: {resume1['state'].get('regression_test_ids')}")

        _banner("STEP 14: Report Generation Agent produced the final briefing")
        report = resume1["state"].get("report")
        if report:
            print(f"recommendation: {report.recommendation}")
            print(f"rationale: {report.recommendation_rationale}")

        if "__interrupt__" not in resume1["state"]:
            print("\nNo final release review was requested — run complete.")
            sys.exit(0)

        _banner("STEP 15: human makes the final high-risk release decision")
        resume2 = resume_evaluation(
            outcome["thread_id"],
            {
                "reviewer": "demo-reviewer@agentgate.local",
                "decision": "approve",
                "justification": "Guardrail verified effective on re-execution; approving release.",
            },
            deps,
            checkpointer,
        )
        _print_state_summary(resume2["state"])

    _banner("DEMO COMPLETE")
    print(f"Inspect this run in the Streamlit UI or via: GET /evaluations/{outcome['run_id']}/report")


if __name__ == "__main__":
    main()
