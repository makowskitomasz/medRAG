"""Regenerate rarerag_overview.png using matplotlib."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch as FBP

BLUE_F = "#dce6f7"
BLUE_E = "#6b8ec7"
RED_F = "#fde2e2"
RED_E = "#d46a6a"
GREEN_F = "#d5f0dc"
GREEN_E = "#5aaa6a"
ORAN_F = "#fdeac8"
ORAN_E = "#d08030"
ARROW = "#333333"
LCOLOR = "#666666"


def rbox(ax, cx, cy, w, h, title, subtitle="", face=BLUE_F, edge=BLUE_E, fs=10.5):
    p = FBP(
        (cx - w / 2, cy - h / 2),
        w,
        h,
        boxstyle="round,pad=0.1",
        linewidth=1.0,
        edgecolor=edge,
        facecolor=face,
        zorder=2,
    )
    ax.add_patch(p)
    if subtitle:
        ax.text(
            cx,
            cy + 0.14,
            title,
            ha="center",
            va="center",
            fontsize=fs,
            fontweight="bold",
            zorder=3,
        )
        ax.text(
            cx,
            cy - 0.20,
            subtitle,
            ha="center",
            va="center",
            fontsize=8.0,
            color="#444444",
            zorder=3,
        )
    else:
        ax.text(
            cx,
            cy,
            title,
            ha="center",
            va="center",
            fontsize=fs,
            fontweight="bold",
            zorder=3,
        )


def ellipse(ax, cx, cy, w, h, text, face, edge, fs=11):
    e = mpatches.Ellipse(
        (cx, cy), w, h, linewidth=1.0, edgecolor=edge, facecolor=face, zorder=2
    )
    ax.add_patch(e)
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fs, zorder=3)


def diamond(ax, cx, cy, w, h, text, face, edge, fs=10):
    pts = [(cx, cy + h / 2), (cx + w / 2, cy), (cx, cy - h / 2), (cx - w / 2, cy)]
    poly = plt.Polygon(
        pts, closed=True, linewidth=1.0, edgecolor=edge, facecolor=face, zorder=2
    )
    ax.add_patch(poly)
    ax.text(
        cx,
        cy,
        text,
        ha="center",
        va="center",
        fontsize=fs,
        fontfamily="monospace",
        zorder=3,
    )


def arr(ax, x0, y0, x1, y1, lbl="", lbl_dx=0, lbl_dy=0.18, lw=1.1):
    ax.annotate(
        "",
        xy=(x1, y1),
        xytext=(x0, y0),
        arrowprops=dict(arrowstyle="-|>", color=ARROW, lw=lw),
        zorder=1,
    )
    if lbl:
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        ax.text(
            mx + lbl_dx,
            my + lbl_dy,
            lbl,
            ha="center",
            va="center",
            fontsize=9,
            color=LCOLOR,
            style="italic",
        )


# ── canvas ────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(7.5, 11))
ax.set_xlim(0, 7.5)
ax.set_ylim(0, 11)
ax.axis("off")

CX = 3.25  # center x for main column

# ── nodes (top → bottom) ──────────────────────────────────────────────────────
# Query q
ellipse(ax, CX, 10.2, 2.0, 0.68, "Query $q$", BLUE_F, BLUE_E)

# Complexity Router diamond
diamond(ax, CX, 8.9, 3.2, 1.0, "Complexity Router", ORAN_F, ORAN_E)

# Hybrid Retrieval
rbox(
    ax,
    CX,
    7.4,
    4.4,
    0.82,
    "Hybrid Retrieval",
    "BM25 + dense vector + cross-encoder reranker",
)

# Set-wise Evidence Selection
rbox(
    ax,
    CX,
    5.9,
    4.4,
    0.82,
    "Set-wise Evidence Selection",
    "greedy complementarity-aware subset scoring",
)

# Grounding Verifier
rbox(
    ax,
    CX,
    4.4,
    4.4,
    0.82,
    "Grounding Verifier",
    "per-claim support check against retrieved context",
)

# Abstention Response (right of Grounding Verifier)
rbox(ax, 6.4, 4.4, 1.5, 0.60, "Abstention\nResponse", face=RED_F, edge=RED_E, fs=9.5)

# LLM Generation
rbox(
    ax, CX, 2.9, 4.4, 0.82, "LLM Generation", "grounded response with inline citations"
)

# Grounded Response
rbox(ax, CX, 1.4, 4.0, 0.65, "Grounded Response", face=GREEN_F, edge=GREEN_E)

# ── arrows ────────────────────────────────────────────────────────────────────
# Query → Router
arr(ax, CX, 9.86, CX, 9.40)

# Router → Hybrid Retrieval ("complex")
arr(ax, CX, 8.40, CX, 7.81, "complex", lbl_dx=0.35, lbl_dy=0.0)

# Hybrid → Set-wise
arr(ax, CX, 6.99, CX, 6.31)

# Set-wise → Grounding Verifier
arr(ax, CX, 5.49, CX, 4.41)

# Grounding Verifier → Abstention (score < τ)
# right edge of Grounding Verifier = CX + 2.2 = 5.45; left edge of Abstention = 6.4-0.75=5.65
arr(ax, CX + 2.2, 4.40, 5.65, 4.40, r"score $< \tau$", lbl_dy=0.20)

# Grounding Verifier → LLM Generation (score ≥ τ)
arr(ax, CX, 3.99, CX, 3.31, r"score $\geq \tau$", lbl_dx=0.55, lbl_dy=0.0)

# Router "simple / fast" → LLM Generation (left bypass)
# from left tip of diamond (CX-1.6, 8.90) down-left to left edge of LLM box (CX-2.4, 2.90)
ax.plot(
    [CX - 1.6, 0.4, 0.4, CX - 2.4], [8.9, 8.9, 2.9, 2.9], color=ARROW, lw=1.1, zorder=1
)
ax.annotate(
    "",
    xy=(CX - 2.4, 2.9),
    xytext=(CX - 2.2, 2.9),
    arrowprops=dict(arrowstyle="-|>", color=ARROW, lw=1.1),
    zorder=2,
)
ax.text(
    0.15,
    6.0,
    "simple /\nfast",
    ha="center",
    va="center",
    fontsize=8.0,
    color=LCOLOR,
    style="italic",
    rotation=90,
    multialignment="center",
)

# LLM Generation → Grounded Response
arr(ax, CX, 2.49, CX, 1.72)

plt.tight_layout(pad=0.3)
plt.savefig("rarerag_overview.png", dpi=200, bbox_inches="tight")
print("Saved rarerag_overview.png")
