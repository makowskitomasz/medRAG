#!/usr/bin/env python3
"""
Generate three new thesis figures from hardcoded benchmark results:
  1. fig_ddi_scatter.png   — Faithfulness vs Answer Correctness (DDI), bubble=latency
  2. fig_ddi_rank_bump.png — Rank bump chart across DDI difficulty levels L1–L5
  3. fig_ddi_quality_bar.png — Side-by-side bars: Faithfulness + Answer Correctness (DDI)

Run from the figures/ directory:
    python gen_new_figures.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

OUT = Path(__file__).parent

# ── colour palette (consistent across all figures) ──────────────────────────
COLORS = {
    "Vanilla": "#4878CF",
    "HyDE": "#6ACC65",
    "Query Rewriting": "#D65F5F",
    "Self-Reflection": "#B47CC7",
    "Multi-Agent": "#C4AD66",
    "Corrective RAG": "#77BEDB",
    "Iterative Multihop": "#F07B26",
    "MADAM-RAG": "#8B8B8B",
    "RARE-RAG": "#E31A1C",
}

MODES_ORDER = list(COLORS.keys())

# ── DDI aggregate results ────────────────────────────────────────────────────
DDI = {
    "Vanilla": dict(faith=0.694, corr=0.487, rel=0.800, lat=29.8),
    "HyDE": dict(faith=0.758, corr=0.514, rel=0.794, lat=51.8),
    "Query Rewriting": dict(faith=0.795, corr=0.539, rel=0.799, lat=49.6),
    "Self-Reflection": dict(faith=0.714, corr=0.452, rel=0.804, lat=55.2),
    "Multi-Agent": dict(faith=0.694, corr=0.493, rel=0.797, lat=27.2),
    "Corrective RAG": dict(faith=0.670, corr=0.462, rel=0.801, lat=33.8),
    "Iterative Multihop": dict(faith=0.751, corr=0.544, rel=0.800, lat=47.4),
    "MADAM-RAG": dict(faith=0.816, corr=0.468, rel=0.794, lat=42.0),
    "RARE-RAG": dict(faith=0.760, corr=0.467, rel=0.795, lat=82.7),
}

# ── DDI per-difficulty answer correctness ────────────────────────────────────
DIFF = {
    "L1": {
        "Vanilla": 0.925,
        "HyDE": 0.940,
        "Query Rewriting": 0.840,
        "Self-Reflection": 0.780,
        "Multi-Agent": 0.860,
        "Corrective RAG": 0.690,
        "Iterative Multihop": 0.790,
        "MADAM-RAG": 0.625,
        "RARE-RAG": 0.710,
    },
    "L2": {
        "Vanilla": 0.300,
        "HyDE": 0.530,
        "Query Rewriting": 0.485,
        "Self-Reflection": 0.385,
        "Multi-Agent": 0.550,
        "Corrective RAG": 0.365,
        "Iterative Multihop": 0.530,
        "MADAM-RAG": 0.555,
        "RARE-RAG": 0.425,
    },
    "L3": {
        "Vanilla": 0.350,
        "HyDE": 0.355,
        "Query Rewriting": 0.315,
        "Self-Reflection": 0.370,
        "Multi-Agent": 0.385,
        "Corrective RAG": 0.350,
        "Iterative Multihop": 0.490,
        "MADAM-RAG": 0.305,
        "RARE-RAG": 0.305,
    },
    "L4": {
        "Vanilla": 0.510,
        "HyDE": 0.430,
        "Query Rewriting": 0.620,
        "Self-Reflection": 0.425,
        "Multi-Agent": 0.305,
        "Corrective RAG": 0.450,
        "Iterative Multihop": 0.485,
        "MADAM-RAG": 0.405,
        "RARE-RAG": 0.425,
    },
    "L5": {
        "Vanilla": 0.350,
        "HyDE": 0.315,
        "Query Rewriting": 0.435,
        "Self-Reflection": 0.300,
        "Multi-Agent": 0.365,
        "Corrective RAG": 0.455,
        "Iterative Multihop": 0.425,
        "MADAM-RAG": 0.450,
        "RARE-RAG": 0.470,
    },
}

LEVELS = ["L1", "L2", "L3", "L4", "L5"]
LEVEL_LABELS = {
    "L1": "L1\nSingle drug",
    "L2": "L2\nTwo drugs",
    "L3": "L3\nMulti-hop",
    "L4": "L4\nPolypharmacy",
    "L5": "L5\nExpert PK/PD",
}


# ─────────────────────────────────────────────────────────────────────────────
# Figure 1: Faithfulness vs Answer Correctness scatter (DDI)
# ─────────────────────────────────────────────────────────────────────────────
def plot_ddi_scatter() -> None:
    fig, ax = plt.subplots(figsize=(8.5, 6.5))

    # compute Pareto frontier (maximise both axes)
    points = [(m, DDI[m]["corr"], DDI[m]["faith"]) for m in MODES_ORDER]
    sorted_pts = sorted(points, key=lambda p: p[1], reverse=True)
    pareto = []
    max_faith = -1.0
    for m, c, f in sorted_pts:
        if f > max_faith:
            pareto.append((c, f))
            max_faith = f
    pareto.sort()
    px, py = zip(*pareto)

    ax.step(px, py, where="post", color="grey", lw=1.2, ls="--", alpha=0.5, zorder=1)
    # label just above the top horizontal segment (y=py[0]=0.816), near its right end
    ax.text(
        px[1] - 0.002,
        py[0] + 0.003,
        "Pareto frontier",
        fontsize=7.5,
        color="grey",
        ha="right",
        va="bottom",
    )

    # bubble size proportional to latency
    lats = np.array([DDI[m]["lat"] for m in MODES_ORDER])
    sizes = (lats / lats.max()) * 600 + 80

    for i, mode in enumerate(MODES_ORDER):
        x = DDI[mode]["corr"]
        y = DDI[mode]["faith"]
        s = sizes[i]
        ax.scatter(
            x,
            y,
            s=s,
            color=COLORS[mode],
            alpha=0.85,
            edgecolors="white",
            linewidths=0.8,
            zorder=3,
        )

    # All labels with thin connector lines — close to their dots
    label_cfg = {
        # dx, dy relative to dot centre; ha = horizontal alignment of text
        "Vanilla": dict(dx=-0.008, dy=-0.017, ha="right"),  # below-left
        "HyDE": dict(dx=0.007, dy=0.012, ha="left"),  # above-right
        "Query Rewriting": dict(
            dx=-0.007, dy=0.011, ha="right"
        ),  # above-left (avoids right edge)
        "Self-Reflection": dict(dx=-0.007, dy=-0.012, ha="right"),  # below-left
        "Multi-Agent": dict(dx=0.007, dy=0.012, ha="left"),  # above-right
        "Corrective RAG": dict(dx=-0.007, dy=0.012, ha="right"),  # above-left
        "Iterative Multihop": dict(dx=0.007, dy=-0.012, ha="left"),  # below-right
        "MADAM-RAG": dict(dx=0.007, dy=0.010, ha="left"),  # above-right
        "RARE-RAG": dict(dx=-0.007, dy=0.010, ha="right"),  # above-left
    }
    for mode in MODES_ORDER:
        x = DDI[mode]["corr"]
        y = DDI[mode]["faith"]
        cfg = label_cfg[mode]
        ax.annotate(
            mode,
            xy=(x, y),
            xytext=(x + cfg["dx"], y + cfg["dy"]),
            fontsize=8.2,
            color=COLORS[mode],
            fontweight="bold",
            ha=cfg["ha"],
            va="center",
            arrowprops=dict(
                arrowstyle="-", color=COLORS[mode], lw=0.5, shrinkA=2, shrinkB=4
            ),
        )

    # size legend — values 30, 55, 80; labelspacing large enough to prevent overlap
    for lat_val, label in [(30, "30 s"), (55, "55 s"), (80, "80 s")]:
        s = (lat_val / lats.max()) * 600 + 80
        ax.scatter([], [], s=s, c="grey", alpha=0.5, label=label, edgecolors="white")
    ax.legend(
        title="Latency (median)",
        loc="lower right",
        fontsize=7.5,
        title_fontsize=8.0,
        framealpha=0.85,
        labelspacing=2.3,
        borderpad=1.2,
        handletextpad=0.8,
        markerscale=0.65,
    )

    ax.set_xlabel("Answer Correctness", fontsize=11)
    ax.set_ylabel("Faithfulness", fontsize=11)
    ax.set_title(
        "DDI Benchmark: Faithfulness vs Answer Correctness\n"
        "(bubble size ∝ median latency)",
        fontsize=12,
    )
    ax.set_xlim(0.42, 0.58)
    ax.set_ylim(0.63, 0.84)
    ax.grid(alpha=0.25, zorder=0)

    fig.tight_layout()
    out = OUT / "fig_ddi_scatter.png"
    fig.savefig(out, dpi=180)
    plt.close(fig)
    print(f"  saved → {out}")


# ─────────────────────────────────────────────────────────────────────────────
# Figure 2: Rank bump chart across DDI difficulty levels
# ─────────────────────────────────────────────────────────────────────────────
def plot_ddi_rank_bump() -> None:
    # compute rank per level (1 = highest correctness)
    ranks: dict[str, list[int]] = {m: [] for m in MODES_ORDER}
    for lvl in LEVELS:
        scores = DIFF[lvl]
        # scipy rankdata would flip direction; do it manually
        sorted_modes = sorted(MODES_ORDER, key=lambda m: scores[m], reverse=True)
        # handle ties with average rank
        rank_map: dict[str, float] = {}
        i = 0
        while i < len(sorted_modes):
            j = i
            while (
                j < len(sorted_modes) - 1
                and scores[sorted_modes[j + 1]] == scores[sorted_modes[j]]
            ):
                j += 1
            avg_rank = (i + j) / 2 + 1
            for k in range(i, j + 1):
                rank_map[sorted_modes[k]] = avg_rank
            i = j + 1
        for m in MODES_ORDER:
            ranks[m].append(rank_map[m])

    x = np.arange(len(LEVELS))
    fig, ax = plt.subplots(figsize=(9, 6))

    # highlight RARE-RAG, QR, Iter Multihop more prominently
    prominent = {"RARE-RAG", "Query Rewriting", "Iterative Multihop", "HyDE", "Vanilla"}

    for mode in MODES_ORDER:
        y = ranks[mode]
        lw = 2.4 if mode in prominent else 1.0
        alpha = 0.95 if mode in prominent else 0.35
        zorder = 5 if mode in prominent else 2
        ax.plot(
            x,
            y,
            "o-",
            color=COLORS[mode],
            lw=lw,
            alpha=alpha,
            markersize=7 if mode in prominent else 4,
            zorder=zorder,
            label=mode,
        )

    # annotate winner stars at each level
    for lvl_idx, lvl in enumerate(LEVELS):
        winner = min(MODES_ORDER, key=lambda m: ranks[m][lvl_idx])
        ax.annotate(
            "★",
            (lvl_idx, 1.0),
            xytext=(lvl_idx, 0.55),
            ha="center",
            fontsize=11,
            color=COLORS[winner],
            fontweight="bold",
            zorder=10,
        )

    ax.set_xticks(x)
    ax.set_xticklabels([LEVEL_LABELS[lvl] for lvl in LEVELS], fontsize=10)
    ax.set_yticks(range(1, 10))
    ax.set_yticklabels([f"#{r}" for r in range(1, 10)], fontsize=9)
    ax.set_ylim(9.5, 0.0)  # rank 1 at top
    ax.set_ylabel("Rank (1 = best answer correctness)", fontsize=10)
    ax.set_title(
        "Architecture Rankings Across DDI Difficulty Levels\n(★ = best at that level)",
        fontsize=12,
    )
    ax.grid(axis="y", alpha=0.2)
    ax.grid(axis="x", alpha=0.1)
    ax.legend(
        loc="lower left",
        fontsize=7.8,
        ncol=2,
        framealpha=0.88,
        bbox_to_anchor=(0.0, 0.0),
    )

    fig.tight_layout()
    out = OUT / "fig_ddi_rank_bump.png"
    fig.savefig(out, dpi=180)
    plt.close(fig)
    print(f"  saved → {out}")


# ─────────────────────────────────────────────────────────────────────────────
# Figure 3: Side-by-side Faithfulness + Answer Correctness bars (DDI)
# Replaces the plain faithfulness-only bar and shows the trade-off clearly
# ─────────────────────────────────────────────────────────────────────────────
def plot_ddi_quality_bar() -> None:
    modes = MODES_ORDER
    x = np.arange(len(modes))
    w = 0.38

    faith_vals = [DDI[m]["faith"] for m in modes]
    corr_vals = [DDI[m]["corr"] for m in modes]

    # sort by faithfulness for readability
    order = sorted(range(len(modes)), key=lambda i: faith_vals[i], reverse=True)
    modes_sorted = [modes[i] for i in order]
    labels_sorted = [modes[i].replace(" ", "\n") for i in order]
    faith_sorted = [faith_vals[i] for i in order]
    corr_sorted = [corr_vals[i] for i in order]

    fig, ax = plt.subplots(figsize=(12, 5.5))
    bars1 = ax.bar(
        x - w / 2,
        faith_sorted,
        w,
        label="Faithfulness",
        color=[COLORS[m] for m in modes_sorted],
        alpha=0.92,
        edgecolor="white",
        linewidth=0.6,
    )
    bars2 = ax.bar(
        x + w / 2,
        corr_sorted,
        w,
        label="Answer Correctness",
        color=[COLORS[m] for m in modes_sorted],
        alpha=0.45,
        edgecolor="white",
        linewidth=0.6,
        hatch="//",
    )

    # value annotations
    for bar in bars1:
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.006,
            f"{bar.get_height():.2f}",
            ha="center",
            va="bottom",
            fontsize=7.5,
            color="black",
        )
    for bar in bars2:
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.006,
            f"{bar.get_height():.2f}",
            ha="center",
            va="bottom",
            fontsize=7.5,
            color="black",
        )

    ax.set_xticks(x)
    ax.set_xticklabels(labels_sorted, fontsize=9)
    ax.set_ylabel("Score", fontsize=11)
    ax.set_ylim(0, 0.92)
    ax.set_title(
        "DDI Benchmark: Faithfulness and Answer Correctness by Architecture\n"
        "(sorted by faithfulness; hatched bars = answer correctness)",
        fontsize=11.5,
    )

    # custom legend
    solid = mpatches.Patch(color="grey", alpha=0.9, label="Faithfulness")
    hatch = mpatches.Patch(
        color="grey", alpha=0.45, hatch="//", label="Answer Correctness"
    )
    ax.legend(handles=[solid, hatch], loc="upper right", fontsize=9, framealpha=0.88)
    ax.grid(axis="y", alpha=0.25)

    fig.tight_layout()
    out = OUT / "fig_ddi_quality_bar.png"
    fig.savefig(out, dpi=180)
    plt.close(fig)
    print(f"  saved → {out}")


if __name__ == "__main__":
    print("Generating figures…")
    plot_ddi_scatter()
    plot_ddi_rank_bump()
    plot_ddi_quality_bar()
    print("Done.")
