"""Regenerate the Chapter 6 figures from results/thesis_final/.

Four figures: quality bars per benchmark, faithfulness by DDI difficulty, and latency.
Run scripts/thesis_final_analysis.py first — this reads the CSVs it writes.

Usage: uv run --with matplotlib --with pandas python scripts/thesis_figures_final.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

IN_DIR = Path("results/thesis_final")
OUT_DIR = Path("thesis-latex/figures")

# Validated categorical palette (see dataviz skill: passes CVD + contrast checks).
BLUE, ORANGE, TEAL, PURPLE = "#3B5BDB", "#E8590C", "#0CA678", "#AE3EC9"
INK, MUTED, GRID = "#1f2124", "#5b6068", "#d8dade"

LABELS = {
    "vanilla": "Vanilla",
    "hyde": "HyDE",
    "query_rewriting": "Query Rewrit.",
    "self_reflection": "Self-Reflect.",
    "corrective_rag": "Corrective",
    "multi_agent": "Multi-Agent",
    "iterative_multihop": "Iter. Multi-hop",
    "madam_rag": "MADAM-RAG",
    "rare_rag": "RARE-RAG",
}
ORDER = list(LABELS)

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.size": 9,
        "axes.edgecolor": MUTED,
        "axes.labelcolor": INK,
        "text.color": INK,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.dpi": 200,
    }
)


def style(ax) -> None:
    ax.yaxis.grid(True, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def quality_bars(df: pd.DataFrame, out: str, title: str) -> None:
    """Faithfulness and answer correctness side by side, sorted by faithfulness."""
    d = df.set_index("rag_mode").loc[ORDER].sort_values("faithfulness", ascending=False)
    x = range(len(d))
    w = 0.38
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    ax.bar([i - w / 2 for i in x], d["faithfulness"], w * 0.94, label="Faithfulness", color=BLUE)
    ax.bar(
        [i + w / 2 for i in x],
        d["answer_correctness"],
        w * 0.94,
        label="Answer correctness",
        color=ORANGE,
    )
    van = df.set_index("rag_mode").loc["vanilla", "faithfulness"]
    ax.axhline(van, color=INK, linewidth=1, linestyle="--", zorder=3)
    ax.text(
        len(d) - 0.4,
        van + 0.012,
        "Vanilla faithfulness",
        ha="right",
        fontsize=7.5,
        color=INK,
    )
    ax.set_xticks(list(x))
    ax.set_xticklabels([LABELS[m] for m in d.index], rotation=30, ha="right", fontsize=8)
    ax.set_ylabel("Score")
    ax.set_ylim(0, 1.05)
    ax.set_title(title, loc="left", fontsize=10, pad=10)
    ax.legend(frameon=False, ncol=2, loc="upper right", fontsize=8)
    style(ax)
    fig.tight_layout()
    fig.savefig(OUT_DIR / out, bbox_inches="tight")
    plt.close(fig)


def difficulty_lines(df: pd.DataFrame, out: str) -> None:
    """Faithfulness by DDI difficulty level: vanilla vs the modes that beat it."""
    piv = df.pivot(index="level", columns="rag_mode", values="faithfulness")
    fig, ax = plt.subplots(figsize=(7.2, 3.6))

    # Everything else recedes into gray; the story is vanilla vs the two winners.
    for mode in ORDER:
        if mode in ("vanilla", "multi_agent", "query_rewriting"):
            continue
        ax.plot(piv.index, piv[mode], color=GRID, linewidth=1.2, zorder=1)

    highlights = [
        ("vanilla", INK, "--", "Vanilla (baseline)"),
        ("multi_agent", BLUE, "-", "Multi-Agent"),
        ("query_rewriting", ORANGE, "-", "Query Rewriting"),
    ]
    for mode, color, ls, label in highlights:
        ax.plot(
            piv.index,
            piv[mode],
            color=color,
            linestyle=ls,
            linewidth=2,
            marker="o",
            markersize=5,
            markeredgecolor="white",
            markeredgewidth=1,
            label=label,
            zorder=3,
        )

    ax.set_xticks([1, 2, 3, 4, 5])
    ax.set_xticklabels(
        [
            "L1\nSingle drug",
            "L2\nTwo drugs",
            "L3\nMulti-hop",
            "L4\nPolypharmacy",
            "L5\nExpert PK/PD",
        ],
        fontsize=8,
    )
    ax.set_ylabel("Faithfulness")
    ax.set_ylim(0.2, 1.0)
    ax.set_title(
        "DDI: faithfulness by question difficulty (other modes in gray)",
        loc="left",
        fontsize=10,
        pad=10,
    )
    ax.legend(frameon=False, fontsize=8, loc="lower left")
    style(ax)
    fig.tight_layout()
    fig.savefig(OUT_DIR / out, bbox_inches="tight")
    plt.close(fig)


def latency_bars(hp: pd.DataFrame, ddi: pd.DataFrame, out: str) -> None:
    """Mean latency per mode on both benchmarks, sorted by the DDI cost."""
    h = hp.set_index("rag_mode")["latency_ms"] / 1000
    d = ddi.set_index("rag_mode")["latency_ms"] / 1000
    order = d.loc[ORDER].sort_values().index
    y = range(len(order))
    hgt = 0.38
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.barh([i + hgt / 2 for i in y], [d[m] for m in order], hgt * 0.94, label="DDI", color=TEAL)
    ax.barh(
        [i - hgt / 2 for i in y], [h[m] for m in order], hgt * 0.94, label="HotpotQA", color=PURPLE
    )
    for i, m in enumerate(order):
        ax.text(d[m] + 1.8, i + hgt / 2, f"{d[m]:.0f}s", va="center", fontsize=7, color=MUTED)
    ax.set_yticks(list(y))
    ax.set_yticklabels([LABELS[m] for m in order], fontsize=8)
    ax.set_xlabel("Mean latency per query (s)")
    ax.set_xlim(0, 145)
    ax.set_title("Cost of each architecture, both benchmarks", loc="left", fontsize=10, pad=10)
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    ax.xaxis.grid(True, color=GRID, linewidth=0.6)
    ax.yaxis.grid(False)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    fig.tight_layout()
    fig.savefig(OUT_DIR / out, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    hp = pd.read_csv(IN_DIR / "hotpotqa.csv")
    ddi = pd.read_csv(IN_DIR / "ddi.csv")
    diff = pd.read_csv(IN_DIR / "ddi_by_difficulty.csv")

    quality_bars(hp, "fig_bar_quality.png", "HotpotQA: faithfulness and answer correctness")
    quality_bars(ddi, "fig_ddi_quality_bar.png", "DDI: faithfulness and answer correctness")
    difficulty_lines(diff, "fig_ddi_faithfulness_by_difficulty.png")
    latency_bars(hp, ddi, "fig_latency.png")
    print(f"wrote 4 figures to {OUT_DIR}")


if __name__ == "__main__":
    main()
