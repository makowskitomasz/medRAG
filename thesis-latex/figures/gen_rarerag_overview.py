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
PAD = 0.1


def rbox(ax, cx, cy, w, h, title, subtitle="", face=BLUE_F, edge=BLUE_E, fs=10.5):
    ax.add_patch(
        FBP(
            (cx - w / 2, cy - h / 2),
            w,
            h,
            boxstyle=f"round,pad={PAD}",
            linewidth=1.0,
            edgecolor=edge,
            facecolor=face,
            zorder=2,
        )
    )
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
    ax.add_patch(
        mpatches.Ellipse(
            (cx, cy),
            w,
            h,
            linewidth=1.0,
            edgecolor=edge,
            facecolor=face,
            zorder=2,
        )
    )
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fs, zorder=3)


def diamond(ax, cx, cy, w, h, text, face, edge, fs=10):
    pts = [(cx, cy + h / 2), (cx + w / 2, cy), (cx, cy - h / 2), (cx - w / 2, cy)]
    ax.add_patch(
        plt.Polygon(
            pts, closed=True, linewidth=1.0, edgecolor=edge, facecolor=face, zorder=2
        )
    )
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
        arrowprops=dict(arrowstyle="-|>", color=ARROW, lw=lw, shrinkA=0, shrinkB=0),
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


def line(ax, xs, ys):
    ax.plot(xs, ys, color=ARROW, lw=1.1, zorder=1)


def arrowhead(ax, x0, y0, x1, y1):
    ax.annotate(
        "",
        xy=(x1, y1),
        xytext=(x0, y0),
        arrowprops=dict(arrowstyle="-|>", color=ARROW, lw=1.1, shrinkA=0, shrinkB=0),
        zorder=2,
    )


# ── canvas ────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(8.5, 11))
ax.set_xlim(-2.2, 8.5)
ax.set_ylim(0, 11)
ax.axis("off")

CX = 3.25  # centre x for main column

# ── Actual box edges  (FancyBboxPatch round,pad=0.1 expands stated rect by PAD)
# rbox(cx, cy, w, h): actual edges = cx ± (w/2 + PAD), cy ± (h/2 + PAD)
#
# Main rboxes  w=4.4  h=0.82  → half_w=2.3  half_h=0.51
#   Hybrid      cy=7.4   top=7.91  bot=6.89  left=0.95  right=5.55
#   Set-wise    cy=5.9   top=6.41  bot=5.39
#   Grounding   cy=4.4   top=4.91  bot=3.89             right=5.55
#   LLM Gen     cy=2.9   top=3.41  bot=2.39  left=0.95
# Grounded Resp cy=1.4  w=4.0 h=0.65 → top=1.825
# Abstention    cx=6.8  w=1.5 h=0.60 → left=5.95  right=7.65
# Diamond       cy=8.9  h=1.0  → top_tip=9.4  bot_tip=8.4  left_tip=(1.65,8.9)
# Ellipse       cy=10.2 h=0.68 → bottom=9.86

# ── nodes ─────────────────────────────────────────────────────────────────────
ellipse(ax, CX, 10.2, 2.0, 0.68, "Query $q$", BLUE_F, BLUE_E)
diamond(ax, CX, 8.9, 3.2, 1.0, "Complexity Router", ORAN_F, ORAN_E)
rbox(
    ax,
    CX,
    7.4,
    4.4,
    0.82,
    "Hybrid Retrieval",
    "BM25 + dense vector + cross-encoder reranker",
)
rbox(
    ax,
    CX,
    5.9,
    4.4,
    0.82,
    "Set-wise Evidence Selection",
    "greedy complementarity-aware subset scoring",
)
rbox(
    ax,
    CX,
    4.4,
    4.4,
    0.82,
    "Grounding Verifier",
    "per-claim support check against retrieved context",
)
rbox(ax, 7.3, 4.4, 1.5, 0.60, "Abstention\nResponse", face=RED_F, edge=RED_E, fs=9.5)
rbox(
    ax, CX, 2.9, 4.4, 0.82, "LLM Generation", "grounded response with inline citations"
)
rbox(ax, CX, 1.4, 4.0, 0.65, "Grounded Response", face=GREEN_F, edge=GREEN_E)

# ── arrows ────────────────────────────────────────────────────────────────────
# Query bottom (9.86) → Router top tip (9.40)
arr(ax, CX, 9.86, CX, 9.40)

# Router bottom tip (8.40) → Hybrid top (7.91)
arr(ax, CX, 8.40, CX, 7.91, "complex", lbl_dx=0.38, lbl_dy=0.0)

# Hybrid bottom (6.89) → Set-wise top (6.41)
arr(ax, CX, 6.89, CX, 6.41)

# Set-wise bottom (5.39) → Grounding top (4.91)
arr(ax, CX, 5.39, CX, 4.91)

# Grounding right (5.55) → Abstention left (5.95)
arr(ax, 5.55, 4.4, 6.45, 4.4, r"score $< \tau$", lbl_dy=0.22)

# Grounding bottom (3.89) → LLM top (3.41)
arr(ax, CX, 3.89, CX, 3.41, r"score $\geq \tau$", lbl_dx=0.5, lbl_dy=0.0)

# LLM bottom (2.39) → Grounded Response top (1.825)
arr(ax, CX, 2.39, CX, 1.825)

# Simple path: Router left → Vanilla Retrieval → LLM Generation
# Add Vanilla Retrieval box on left side
SIMPLE_X = -0.8
rbox(ax, SIMPLE_X, 5.9, 2.2, 0.82, "Vanilla Retrieval", "basic vector search", fs=9.5)

# Router left tip (1.65, 8.9) → down → Vanilla Retrieval top
line(ax, [1.65, SIMPLE_X, SIMPLE_X], [8.9, 8.9, 6.41])
arrowhead(ax, SIMPLE_X, 6.6, SIMPLE_X, 6.41)
ax.text(
    0.4,
    8.9 + 0.18,
    "simple",
    ha="center",
    va="center",
    fontsize=9,
    color=LCOLOR,
    style="italic",
)

# Vanilla Retrieval bottom → LLM left edge
line(ax, [SIMPLE_X, SIMPLE_X, 0.65], [5.39, 2.9, 2.9])
arrowhead(ax, 0.65, 2.9, 0.95, 2.9)

plt.tight_layout(pad=0.3)
plt.savefig("rarerag_overview.png", dpi=200, bbox_inches="tight")
print("Saved rarerag_overview.png")
