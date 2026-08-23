"""Evaluation harness: runs the 20-query test set through the pipeline, both with
and without Mem0 memory enabled, and reports FCR / escalation precision & recall.

Run with: uv run python eval/run_eval.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

load_dotenv()

import graph as graph_module  # noqa: E402
import memory as memory_module  # noqa: E402

EVAL_DIR = Path(__file__).resolve().parent
QUERIES_PATH = EVAL_DIR / "test_queries.json"
REPORT_PATH = EVAL_DIR / "results_report.md"


def load_queries() -> list[dict]:
    with open(QUERIES_PATH) as f:
        return json.load(f)


def run_pass(queries: list[dict], *, memory_enabled: bool, shared_customer_id: str | None) -> list[dict]:
    memory_module.MEMORY_ENABLED = memory_enabled
    rows = []
    for i, q in enumerate(queries):
        customer_id = shared_customer_id or f"eval-{q['id']}"
        try:
            result = graph_module.run(customer_id, q["query"])
            bot_decision = "escalate" if result["escalate"] else "answer"
            error = None
        except Exception as e:
            result = {"confidence": 0.0, "category": q["category"], "citations": [], "escalate": True}
            bot_decision = "escalate"
            error = str(e)

        expected = q["expected_decision"]
        rows.append(
            {
                "id": q["id"],
                "query": q["query"],
                "category": q["category"],
                "expected_decision": expected,
                "bot_decision": bot_decision,
                "correct": bot_decision == expected,
                "confidence": result.get("confidence", 0.0),
                "has_citations": bool(result.get("citations")),
                "answer_without_citations": bot_decision == "answer" and not result.get("citations"),
                "error": error,
            }
        )
    return rows


def compute_stats(rows: list[dict]) -> dict:
    total = len(rows)
    fcr = sum(1 for r in rows if r["bot_decision"] == "answer" and r["expected_decision"] == "answer") / total

    tp = sum(1 for r in rows if r["bot_decision"] == "escalate" and r["expected_decision"] == "escalate")
    fp = sum(1 for r in rows if r["bot_decision"] == "escalate" and r["expected_decision"] == "answer")
    fn = sum(1 for r in rows if r["bot_decision"] == "answer" and r["expected_decision"] == "escalate")

    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    recall = tp / (tp + fn) if (tp + fn) else float("nan")
    accuracy = sum(1 for r in rows if r["correct"]) / total
    possible_hallucinations = sum(1 for r in rows if r["answer_without_citations"])

    return {
        "total": total,
        "fcr": fcr,
        "accuracy": accuracy,
        "escalation_precision": precision,
        "escalation_recall": recall,
        "possible_hallucinations": possible_hallucinations,
    }


def render_table(rows: list[dict]) -> str:
    header = "| ID | Category | Expected | Bot | Correct | Confidence | Citations? |\n"
    header += "|---|---|---|---|---|---|---|\n"
    lines = []
    for r in rows:
        lines.append(
            f"| {r['id']} | {r['category']} | {r['expected_decision']} | {r['bot_decision']} | "
            f"{'✅' if r['correct'] else '❌'} | {r['confidence']:.2f} | {'yes' if r['has_citations'] else 'no'} |"
        )
    return header + "\n".join(lines)


def render_stats(title: str, stats: dict) -> str:
    return (
        f"### {title}\n\n"
        f"- **First-Contact Resolution (FCR):** {stats['fcr']:.0%} ({stats['total']} queries)\n"
        f"- **Overall decision accuracy vs. expected label:** {stats['accuracy']:.0%}\n"
        f"- **Escalation precision:** {stats['escalation_precision']:.0%}\n"
        f"- **Escalation recall:** {stats['escalation_recall']:.0%}\n"
        f"- **Answers with no citations (manual hallucination-check candidates):** "
        f"{stats['possible_hallucinations']}\n"
    )


def render_overall_summary(
    rows_no_memory: list[dict],
    stats_no_memory: dict,
    rows_with_memory: list[dict],
    stats_with_memory: dict,
) -> str:
    def pct_row(label: str, key: str) -> str:
        return f"| {label} | {stats_no_memory[key]:.0%} | {stats_with_memory[key]:.0%} |"

    lines = ["## Summary", ""]
    lines.append("| Metric | Without memory | With memory |")
    lines.append("|---|---|---|")
    lines.append(pct_row("First-Contact Resolution (FCR)", "fcr"))
    lines.append(pct_row("Overall decision accuracy vs. expected label", "accuracy"))
    lines.append(pct_row("Escalation precision", "escalation_precision"))
    lines.append(pct_row("Escalation recall", "escalation_recall"))
    lines.append(
        f"| Possible-hallucination flags (answers with no citations) | "
        f"{stats_no_memory['possible_hallucinations']} | {stats_with_memory['possible_hallucinations']} |"
    )
    lines.append("")

    for title, rows in [("without memory", rows_no_memory), ("with memory", rows_with_memory)]:
        misses = [r for r in rows if not r["correct"]]
        lines.append(f"**Missed expected label ({title}):**")
        if misses:
            for r in misses:
                lines.append(
                    f"- {r['id']} ({r['category']}): expected `{r['expected_decision']}`, "
                    f"bot said `{r['bot_decision']}` at confidence {r['confidence']:.2f}"
                )
        else:
            lines.append("- none")
        lines.append("")

    by_id_no_memory = {r["id"]: r for r in rows_no_memory}
    by_id_with_memory = {r["id"]: r for r in rows_with_memory}
    changed = [
        (qid, by_id_no_memory[qid]["bot_decision"], by_id_with_memory[qid]["bot_decision"])
        for qid in by_id_no_memory
        if by_id_no_memory[qid]["bot_decision"] != by_id_with_memory[qid]["bot_decision"]
    ]
    lines.append("**Queries where memory changed the bot's decision vs. the no-memory run:**")
    if changed:
        for qid, no_mem_decision, with_mem_decision in changed:
            lines.append(f"- {qid}: `{no_mem_decision}` → `{with_mem_decision}`")
    else:
        lines.append("- none — identical decisions in both passes")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    queries = load_queries()

    print(f"Running {len(queries)} queries WITHOUT memory...")
    rows_no_memory = run_pass(queries, memory_enabled=False, shared_customer_id=None)
    stats_no_memory = compute_stats(rows_no_memory)

    print(f"Running {len(queries)} queries WITH memory (shared customer_id, sequential)...")
    SHARED_CUSTOMER_ID = "eval-shared-customer"
    memory_module.MEMORY_ENABLED = True
    memory_module.reset_customer_memory(SHARED_CUSTOMER_ID)  # Mem0 is a persistent hosted store —
    # without this, memory accumulates across separate eval runs and later runs get contaminated
    # by escalations/issues left over from earlier ones, making the pass non-reproducible.
    time.sleep(3)  # Mem0's delete is async ("delete in progress") — give it a moment to land
    rows_with_memory = run_pass(queries, memory_enabled=True, shared_customer_id=SHARED_CUSTOMER_ID)
    stats_with_memory = compute_stats(rows_with_memory)

    langsmith_project = os.environ.get("LANGCHAIN_PROJECT", "default")
    tracing_on = os.environ.get("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    langsmith_note = (
        f"Traces recorded under LangSmith project `{langsmith_project}` — see https://smith.langchain.com/"
        if tracing_on
        else "LangSmith tracing was not enabled for this run (set LANGCHAIN_TRACING_V2=true to capture traces)."
    )

    report = f"""# Evaluation Report

Generated by `eval/run_eval.py` against the 20-query test set in `eval/test_queries.json`.

{langsmith_note}

## Without Memory

{render_stats("Summary", stats_no_memory)}

{render_table(rows_no_memory)}

## With Memory (shared customer, sequential run)

{render_stats("Summary", stats_with_memory)}

{render_table(rows_with_memory)}

## Notes

- "Answers with no citations" is an automated proxy for possible hallucination — it flags any
  surfaced answer that cited no source document. It does not replace manually reading each
  answer against the source tickets/FAQs/pricing docs, which should still be done before
  trusting these numbers.
- The memory-on pass reuses a single customer_id across all 20 queries in order, so prior
  escalations can accumulate and trigger the memory-override rule (2+ prior escalations in a
  category forces escalation). The memory-off pass uses a fresh customer_id per query.

{render_overall_summary(rows_no_memory, stats_no_memory, rows_with_memory, stats_with_memory)}"""

    REPORT_PATH.write_text(report)
    print(f"Wrote {REPORT_PATH}")
    print(render_stats("Without memory", stats_no_memory))
    print(render_stats("With memory", stats_with_memory))


if __name__ == "__main__":
    main()
