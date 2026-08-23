"""Generates the hand-drawn-style architecture diagram (PNG + SVG).

Not part of the runtime app — a one-off build script for Document/architecture-diagram.*
Run with: uv run python Document/generate_diagram.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, Ellipse, Rectangle, FancyArrowPatch

OUT_DIR = Path(__file__).resolve().parent
LAVENDER = "#9b8fd4"
PURPLE = "#6c4fb8"
BLUE = "#4a6fd4"
GREEN = "#2fa84f"
INK = "#2e2a3d"
BG = "#ffffff"

STAGES = [
    {
        "num": 1,
        "title": "Customer Query +\nMemory Lookup",
        "sub": "(Mem0)",
        "note": "Mem0 Platform API",
        "icon": "person",
    },
    {
        "num": 2,
        "title": "Intent\nClassification",
        "sub": "(category tagging)",
        "note": "OpenAI gpt-4o-mini\n(structured output)",
        "icon": "ai",
    },
    {
        "num": 3,
        "title": "Hybrid\nRetrieval",
        "sub": "(Pinecone + BM25)",
        "note": "Pinecone dense +\nin-memory BM25 (RRF)",
        "icon": "db",
    },
    {
        "num": 4,
        "title": "Rerank &\nConfidence Scoring",
        "sub": "",
        "note": "EnsembleRetriever RRF +\ngpt-4o-mini confidence",
        "icon": "ai",
    },
    {
        "num": 5,
        "title": "LangGraph Decision",
        "sub": "Answer vs. Escalate",
        "note": "LangGraph StateGraph",
        "icon": "doc",
    },
    {
        "num": 6,
        "title": "Escalation Handoff /\nAnswer Delivered",
        "sub": "(to human agent)",
        "note": "Streamlit UI",
        "icon": "check",
    },
]


def draw_person_icon(ax, cx, cy, scale=1.0):
    ax.add_patch(Circle((cx, cy + 0.09 * scale), 0.045 * scale, facecolor="none", edgecolor=INK, linewidth=1.6))
    ax.add_patch(
        FancyBboxPatch(
            (cx - 0.07 * scale, cy - 0.09 * scale),
            0.14 * scale,
            0.12 * scale,
            boxstyle="round,pad=0,rounding_size=0.03",
            facecolor="none",
            edgecolor=INK,
            linewidth=1.6,
        )
    )


def draw_ai_icon(ax, cx, cy, scale=1.0):
    ax.add_patch(
        FancyBboxPatch(
            (cx - 0.13 * scale, cy - 0.1 * scale),
            0.26 * scale,
            0.2 * scale,
            boxstyle="round,pad=0,rounding_size=0.03",
            facecolor="none",
            edgecolor=PURPLE,
            linewidth=1.6,
        )
    )
    ax.text(cx, cy - 0.005 * scale, "AI", ha="center", va="center", fontsize=11, color=PURPLE, fontweight="bold")


def draw_db_icon(ax, cx, cy, scale=1.0):
    w, h = 0.16 * scale, 0.16 * scale
    ax.add_patch(Ellipse((cx, cy + h / 2), w, 0.05 * scale, facecolor="none", edgecolor=BLUE, linewidth=1.6))
    ax.add_patch(Rectangle((cx - w / 2, cy - h / 2), w, h, facecolor="none", edgecolor=BLUE, linewidth=1.6))
    ax.add_patch(Ellipse((cx, cy - h / 2), w, 0.05 * scale, facecolor="none", edgecolor=BLUE, linewidth=1.6))


def draw_doc_icon(ax, cx, cy, scale=1.0):
    w, h = 0.12 * scale, 0.16 * scale
    ax.add_patch(Rectangle((cx - w / 2, cy - h / 2), w, h, facecolor="none", edgecolor=INK, linewidth=1.6))
    for frac in (0.25, 0.5, 0.75):
        ax.plot(
            [cx - w / 2 + 0.02, cx + w / 2 - 0.02],
            [cy - h / 2 + h * frac, cy - h / 2 + h * frac],
            color=INK,
            linewidth=1.1,
        )


def draw_check_icon(ax, cx, cy, scale=1.0):
    ax.plot(
        [cx - 0.08 * scale, cx - 0.02 * scale, cx + 0.09 * scale],
        [cy, cy - 0.06 * scale, cy + 0.08 * scale],
        color=GREEN,
        linewidth=3.2,
        solid_capstyle="round",
    )


ICON_DRAWERS = {"person": draw_person_icon, "ai": draw_ai_icon, "db": draw_db_icon, "doc": draw_doc_icon, "check": draw_check_icon}


def main() -> None:
    with plt.xkcd(scale=1, length=110, randomness=2):
        fig, ax = plt.subplots(figsize=(16, 9), dpi=200)
        fig.patch.set_facecolor(BG)
        ax.set_facecolor(BG)
        ax.set_xlim(0, 16)
        ax.set_ylim(0, 9)
        ax.axis("off")

        ax.text(
            8,
            8.45,
            "SaaS Billing Support Bot — Hybrid RAG + Escalation Pipeline",
            ha="center",
            va="center",
            fontsize=21,
            color=INK,
            fontweight="bold",
        )
        ax.text(
            8,
            7.95,
            "Hybrid retrieval + confidence-gated escalation — the bot never guesses on money or low-confidence answers",
            ha="center",
            va="center",
            fontsize=12,
            color="#5c5670",
        )

        n = len(STAGES)
        box_w, box_h = 2.15, 2.6
        gap = 0.35
        total_w = n * box_w + (n - 1) * gap
        start_x = (16 - total_w) / 2
        y_center = 4.7

        centers = []
        for i, stage in enumerate(STAGES):
            x = start_x + i * (box_w + gap)
            centers.append((x, x + box_w))

            box = FancyBboxPatch(
                (x, y_center - box_h / 2),
                box_w,
                box_h,
                boxstyle="round,pad=0.02,rounding_size=0.15",
                facecolor="#faf9ff",
                edgecolor=LAVENDER,
                linewidth=2.0,
            )
            ax.add_patch(box)

            badge_cx, badge_cy = x + 0.28, y_center + box_h / 2 - 0.28
            ax.add_patch(Circle((badge_cx, badge_cy), 0.22, facecolor="white", edgecolor=PURPLE, linewidth=2.2))
            ax.text(badge_cx, badge_cy, str(stage["num"]), ha="center", va="center", fontsize=13, color=PURPLE, fontweight="bold")

            icon_cx = x + box_w / 2
            icon_cy = y_center + box_h / 2 - 0.75
            ICON_DRAWERS[stage["icon"]](ax, icon_cx, icon_cy, scale=1.3)

            ax.text(
                x + box_w / 2,
                y_center + 0.05,
                stage["title"],
                ha="center",
                va="center",
                fontsize=11.5,
                color=INK,
                fontweight="bold",
            )
            if stage["sub"]:
                ax.text(
                    x + box_w / 2,
                    y_center - box_h / 2 + 0.45,
                    stage["sub"],
                    ha="center",
                    va="center",
                    fontsize=9.5,
                    color="#5c5670",
                    style="italic",
                )

            note_y = y_center - box_h / 2 - 0.55
            note_box = FancyBboxPatch(
                (x + 0.05, note_y - 0.42),
                box_w - 0.1,
                0.75,
                boxstyle="round,pad=0.02,rounding_size=0.08",
                facecolor="#ffffff",
                edgecolor="#8b84a8",
                linewidth=1.1,
                linestyle=(0, (4, 3)),
            )
            ax.add_patch(note_box)
            ax.text(
                x + box_w / 2,
                note_y - 0.05,
                stage["note"],
                ha="center",
                va="center",
                fontsize=8.3,
                color="#443f5a",
            )

        for i in range(n - 1):
            x0 = centers[i][1]
            x1 = centers[i + 1][0]
            arrow = FancyArrowPatch(
                (x0 + 0.05, y_center),
                (x1 - 0.05, y_center),
                arrowstyle="-|>",
                mutation_scale=22,
                linewidth=2.4,
                color=BLUE,
            )
            ax.add_patch(arrow)

        ax.text(
            8,
            0.45,
            "answer delivered ✓      escalation sent ✓      —  green checkmarks mark successful terminal operations",
            ha="center",
            va="center",
            fontsize=10.5,
            color=GREEN,
            fontweight="bold",
        )

        fig.savefig(OUT_DIR / "architecture-diagram.png", facecolor=BG, bbox_inches="tight")
        fig.savefig(OUT_DIR / "architecture-diagram.svg", facecolor=BG, bbox_inches="tight")
        print("Wrote architecture-diagram.png and .svg")


if __name__ == "__main__":
    main()
