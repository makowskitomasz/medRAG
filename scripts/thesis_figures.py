"""
Generate benchmark figures for the Master's thesis (Chapter 6).

Usage:
    uv run python scripts/thesis_figures.py

Outputs (all to thesis-latex/figures/):
    fig_radar.pdf          — radar chart: 5 RAGAS metrics across all modes
    fig_bar_quality.pdf    — grouped bar: token_f1 / faithfulness / answer_correctness
    fig_latency.pdf        — horizontal bar: mean latency + p95 whisker
    fig_pareto.pdf         — scatter: faithfulness vs token_f1, bubble = latency
    fig_heatmap.pdf        — heatmap: all 7 metrics, z-scored
"""

import math
from pathlib import Path

import matplotlib
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

matplotlib.use("Agg")

# ── paths ────────────────────────────────────────────────────────────────────
REPO = Path(__file__).resolve().parent.parent
CSV = REPO / "results" / "hotpotqa_final" / "summary_table.csv"
OUT = REPO / "thesis-latex" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

# ── load data ─────────────────────────────────────────────────────────────────
df = pd.read_csv(CSV)

DISPLAY = {
    "vanilla": "Vanilla RAG",
    "hyde": "HyDE",
    "query_rewriting": "Query Rewriting",
    "self_reflection": "Self-RAG",
    "multi_agent": "Multi-Agent",
    "corrective_rag": "Corrective RAG",
    "iterative_multihop": "Iterative Multi-hop",
    "madam_rag": "MADAM-RAG",
    "rare_rag": "RARE-RAG",
}
df["label"] = df["rag_mode"].map(DISPLAY)

# Consistent colour per mode (RARE-RAG always orange/accent)
PALETTE = [
    "#4878CF",
    "#6ACC65",
    "#D65F5F",
    "#B47CC7",
    "#C4AD66",
    "#77BEDB",
    "#F28E2B",
    "#E15759",
    "#FF9D00",
]
color_map = {row.label: PALETTE[i] for i, row in df.iterrows()}
color_map["RARE-RAG"] = "#FF9D00"  # force accent

RARE_COLOR = "#FF9D00"
OTHER_ALPHA = 0.75

# ── shared style ─────────────────────────────────────────────────────────────
plt.rcParams.update(
    {
        "font.family": "serif",
        "font.size": 10,
        "axes.titlesize": 11,
        "axes.labelsize": 10,
        "legend.fontsize": 8,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.05,
    }
)


# ════════════════════════════════════════════════════════════════════════════
# 1. RADAR CHART — 5 RAGAS metrics
# ════════════════════════════════════════════════════════════════════════════
def plot_radar():
    metrics = [
        "faithfulness",
        "answer_correctness",
        "answer_relevance",
        "context_recall",
        "token_f1",
    ]
    labels = [
        "Faithfulness",
        "Answer\nCorrectness",
        "Answer\nRelevance",
        "Context\nRecall",
        "Token F1",
    ]

    n = len(metrics)
    angles = [i * 2 * math.pi / n for i in range(n)]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(5.5, 5.5), subplot_kw={"polar": True})

    for _, row in df.iterrows():
        vals = [row[m] for m in metrics]
        vals += vals[:1]
        lw = 2.2 if row.label == "RARE-RAG" else 1.0
        col = color_map[row.label]
        alp = 1.0 if row.label == "RARE-RAG" else OTHER_ALPHA
        ax.plot(angles, vals, linewidth=lw, color=col, alpha=alp, label=row.label)
        ax.fill(angles, vals, alpha=0.04 if row.label != "RARE-RAG" else 0.12, color=col)

    ax.set_thetagrids([a * 180 / math.pi for a in angles[:-1]], labels)
    ax.set_ylim(0.45, 1.02)
    ax.set_yticks([0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
    ax.set_yticklabels(["0.5", "0.6", "0.7", "0.8", "0.9", "1.0"], fontsize=7)
    ax.grid(color="grey", linestyle="--", linewidth=0.4, alpha=0.6)

    handles = [
        mpatches.Patch(
            color=color_map[lbl], label=lbl, alpha=1.0 if lbl == "RARE-RAG" else OTHER_ALPHA
        )
        for lbl in df["label"]
    ]
    ax.legend(
        handles=handles,
        loc="upper right",
        bbox_to_anchor=(1.38, 1.18),
        framealpha=0.9,
        fontsize=7.5,
    )

    ax.set_title(
        "RAGAS Metric Profiles — All RAG Modes\n(HotpotQA, $n=1{,}000$)", pad=18, fontsize=11
    )
    fig.savefig(OUT / "fig_radar.png", dpi=300)
    plt.close(fig)
    print("✓  fig_radar.png")


# ════════════════════════════════════════════════════════════════════════════
# 2. GROUPED BAR — Token F1 / Faithfulness / Answer Correctness
# ════════════════════════════════════════════════════════════════════════════
def plot_bar_quality():
    metrics = ["token_f1", "faithfulness", "answer_correctness"]
    mlabels = ["Token F1", "Faithfulness", "Answer Correctness"]

    d = df.sort_values("faithfulness", ascending=False).reset_index(drop=True)
    x = np.arange(len(d))
    width = 0.26

    fig, ax = plt.subplots(figsize=(10, 4.2))

    bar_colors = ["#4878CF", "#D65F5F", "#6ACC65"]
    for i, (col, ml) in enumerate(zip(metrics, mlabels, strict=False)):
        bars = ax.bar(
            x + (i - 1) * width, d[col], width, label=ml, color=bar_colors[i], alpha=0.85, zorder=3
        )
        # highlight RARE-RAG bars
        for j, bar in enumerate(bars):
            if d.iloc[j]["label"] == "RARE-RAG":
                bar.set_edgecolor("black")
                bar.set_linewidth(1.5)

    ax.set_xticks(x)
    ax.set_xticklabels(d["label"], rotation=30, ha="right", fontsize=8.5)
    ax.set_ylabel("Score")
    ax.set_ylim(0, 1.08)
    ax.set_title("Quality Metrics by RAG Mode (HotpotQA, $n=1{,}000$)")
    ax.yaxis.grid(True, linestyle="--", alpha=0.5, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(loc="upper right", framealpha=0.9)

    fig.savefig(OUT / "fig_bar_quality.png", dpi=300)
    plt.close(fig)
    print("✓  fig_bar_quality.png")


# ════════════════════════════════════════════════════════════════════════════
# 3. LATENCY — horizontal bar + p95 whisker
# ════════════════════════════════════════════════════════════════════════════
def plot_latency():
    d = df.sort_values("latency_ms_mean").reset_index(drop=True)
    y = np.arange(len(d))

    fig, ax = plt.subplots(figsize=(7, 4.0))

    colors = [RARE_COLOR if lbl == "RARE-RAG" else "#4878CF" for lbl in d["label"]]
    ax.barh(y, d["latency_ms_mean"] / 1000, color=colors, alpha=0.85, zorder=3, height=0.6)

    # p95 whisker
    for i, (_, row) in enumerate(d.iterrows()):
        mean_s = row["latency_ms_mean"] / 1000
        p95_s = row["latency_ms_p95"] / 1000
        ax.plot([mean_s, p95_s], [i, i], color="black", linewidth=1.2, zorder=4)
        ax.plot(p95_s, i, "|", color="black", markersize=5, zorder=4)

    ax.set_yticks(y)
    ax.set_yticklabels(d["label"], fontsize=8.5)
    ax.set_xlabel("Latency (seconds)")
    ax.set_title("Mean Query Latency with p95 (HotpotQA, $n=1{,}000$)")
    ax.xaxis.grid(True, linestyle="--", alpha=0.5, zorder=0)
    ax.set_axisbelow(True)

    rare_patch = mpatches.Patch(color=RARE_COLOR, label="RARE-RAG")
    other_patch = mpatches.Patch(color="#4878CF", label="Other modes")
    ax.legend(handles=[rare_patch, other_patch], loc="lower right", framealpha=0.9)

    fig.savefig(OUT / "fig_latency.png", dpi=300)
    plt.close(fig)
    print("✓  fig_latency.png")


# ════════════════════════════════════════════════════════════════════════════
# 4. PARETO SCATTER — faithfulness vs token_f1, leader-line labels
# ════════════════════════════════════════════════════════════════════════════
def plot_pareto():
    # All points are tightly clustered, so labels are placed in two side
    # columns connected to their points by thin leader lines.
    fig, ax = plt.subplots(figsize=(9.5, 5.2))

    lat_min = df["latency_ms_mean"].min()
    lat_max = df["latency_ms_mean"].max()

    # ── draw bubbles ─────────────────────────────────────────────────────
    for _, row in df.iterrows():
        lat = row["latency_ms_mean"]
        size = 90 + 500 * (lat - lat_min) / (lat_max - lat_min)
        col = RARE_COLOR if row.label == "RARE-RAG" else color_map[row.label]
        alp = 1.0 if row.label == "RARE-RAG" else 0.78
        ec = "black" if row.label == "RARE-RAG" else "white"
        lw = 1.5 if row.label == "RARE-RAG" else 0.6
        ax.scatter(
            row["token_f1"],
            row["faithfulness"],
            s=size,
            color=col,
            alpha=alp,
            zorder=4,
            edgecolors=ec,
            linewidths=lw,
        )

    # ── leader-line label layout ─────────────────────────────────────────
    # Left column  (ha="right")  x_text = 0.478
    # Right column (ha="left")   x_text = 0.549
    # Points sorted into left/right by token_f1 split ≈ 0.536
    X_LEFT = 0.478
    X_RIGHT = 0.550

    left_modes = [
        "MADAM-RAG",
        "Multi-Agent",
        "Iterative Multi-hop",
        "Vanilla RAG",
        "Query Rewriting",
    ]
    right_modes = ["Corrective RAG", "HyDE", "Self-RAG", "RARE-RAG"]

    # evenly space labels vertically within the y-axis range
    y_lo, y_hi = 0.934, 0.982
    left_ys = np.linspace(y_hi, y_lo, len(left_modes))
    right_ys = np.linspace(y_hi, y_lo, len(right_modes))

    label_pos = {}
    for lab, y_ in zip(left_modes, left_ys, strict=False):
        label_pos[lab] = (X_LEFT, y_, "right")
    for lab, y_ in zip(right_modes, right_ys, strict=False):
        label_pos[lab] = (X_RIGHT, y_, "left")

    arrow_kw = dict(
        arrowstyle="-", color="grey", lw=0.65, shrinkA=0, shrinkB=4, connectionstyle="arc3,rad=0.0"
    )

    for _, row in df.iterrows():
        lx, ly, ha = label_pos[row.label]
        weight = "bold" if row.label == "RARE-RAG" else "normal"
        ax.annotate(
            row.label,
            xy=(row["token_f1"], row["faithfulness"]),
            xytext=(lx, ly),
            ha=ha,
            va="center",
            fontsize=8.5,
            fontweight=weight,
            arrowprops=arrow_kw,
            zorder=5,
        )

    # ── axes ──────────────────────────────────────────────────────────────
    ax.set_xlim(0.470, 0.558)
    ax.set_ylim(0.930, 0.984)
    ax.set_xlabel("Token F1", labelpad=6)
    ax.set_ylabel("Faithfulness", labelpad=6)
    ax.set_title(
        "Faithfulness vs. Token F1  (HotpotQA, $n=1{,}000$)\n"
        "Bubble size $\\propto$ mean query latency",
        fontsize=11,
    )
    ax.xaxis.grid(True, linestyle="--", alpha=0.35, zorder=0)
    ax.yaxis.grid(True, linestyle="--", alpha=0.35, zorder=0)
    ax.set_axisbelow(True)

    # ── latency bubble legend ─────────────────────────────────────────────
    for lat_val, lab in [(9000, "9 s"), (20000, "20 s"), (45000, "45 s")]:
        s = 90 + 500 * (lat_val - lat_min) / (lat_max - lat_min)
        ax.scatter([], [], s=s, color="grey", alpha=0.55, label=lab)
    ax.legend(title="Latency", loc="lower right", framealpha=0.92, fontsize=8, title_fontsize=8)

    fig.savefig(OUT / "fig_pareto.png", dpi=300)
    plt.close(fig)
    print("✓  fig_pareto.png")


# ════════════════════════════════════════════════════════════════════════════
# 5. HEATMAP — all 7 metrics, z-scored per column
# ════════════════════════════════════════════════════════════════════════════
def plot_heatmap():
    metrics = [
        "token_f1",
        "em",
        "rouge_l",
        "faithfulness",
        "answer_correctness",
        "answer_relevance",
        "context_recall",
    ]
    col_labels = [
        "Token F1",
        "EM",
        "ROUGE-L",
        "Faithfulness",
        "Ans. Corr.",
        "Ans. Rel.",
        "Ctx. Recall",
    ]

    d = df.set_index("label")[metrics]
    z = (d - d.mean()) / d.std()

    # row order: sort by faithfulness desc
    order = df.sort_values("faithfulness", ascending=False)["label"].tolist()
    z = z.loc[order]
    raw = d.loc[order]

    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    im = ax.imshow(z.values, aspect="auto", cmap="RdYlGn", vmin=-2.5, vmax=2.5)

    ax.set_xticks(range(len(col_labels)))
    ax.set_xticklabels(col_labels, rotation=30, ha="right", fontsize=8.5)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(order, fontsize=8.5)

    # annotate with raw values
    for i in range(len(order)):
        for j, col in enumerate(metrics):
            val = raw.iloc[i][col]
            fmt = f"{val:.3f}" if col != "em" else f"{val:.3f}"
            txt_col = "black" if abs(z.values[i, j]) < 1.5 else "white"
            ax.text(j, i, fmt, ha="center", va="center", fontsize=7, color=txt_col)

    plt.colorbar(im, ax=ax, label="z-score", shrink=0.8)
    ax.set_title("All Metrics — Z-scored Heatmap (HotpotQA, $n=1{,}000$)")

    # bold RARE-RAG row label
    for tick in ax.get_yticklabels():
        if tick.get_text() == "RARE-RAG":
            tick.set_fontweight("bold")

    fig.savefig(OUT / "fig_heatmap.png", dpi=300)
    plt.close(fig)
    print("✓  fig_heatmap.png")


# ════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    plot_radar()
    plot_bar_quality()
    plot_latency()
    plot_pareto()
    plot_heatmap()
    print(f"\nAll figures saved to: {OUT}")
