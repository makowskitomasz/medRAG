"""Generate rag_timeline.png using matplotlib (no LaTeX required)."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch as FBP

# ── layout constants ──────────────────────────────────────────────────────────
YEARS = [2020, 2021, 2022, 2023, 2024, 2025, 2026]
X = {y: i * 2.0 for i, y in enumerate(YEARS)}  # x position per year

Y_AXIS = 0.0
Y_UP1 = 1.6  # upper row 1
Y_UP2 = 3.2  # upper row 2 (stacked: DPR above RAG, RAPTOR above GraphRAG)
Y_DN = -1.6  # lower row

BOX_W = 0.82  # box half-width  (spacing=2.0, so gap=0.36 between boxes)
BOX_H = 0.50  # box half-height
YEAR_W = 0.55  # year-label half-width
YEAR_H = 0.27

BLUE_FACE = "#dce6f7"
BLUE_EDGE = "#6b8ec7"
TEAL_FACE = "#d5f0ec"
TEAL_EDGE = "#3a9e8e"
YEAR_FACE = "#e8e8e8"
YEAR_EDGE = "#999999"
LINE_COL = "#aaaaaa"

# ── data ──────────────────────────────────────────────────────────────────────
upper1 = [
    (2020, "RAG", "Lewis et al."),
    (2022, "HyDE", "Gao et al."),
    (2023, "Self-RAG", "Asai et al."),
    (2024, "GraphRAG", "Edge et al."),
    (2025, "Chain-of-Retr.", "Wang et al."),
    (2026, "A-RAG", "Du et al."),
]
upper2 = [
    (2020, "DPR", "Karpukhin et al."),  # stacked above RAG
    (2024, "RAPTOR", "Sarthi et al."),  # stacked above GraphRAG
]
lower = [
    (2020, "ColBERT", "Khattab & Z."),
    (2021, "BEIR", "Thakur et al."),
    (2022, "ColBERTv2", "Santhanam et al."),
    (2023, "RAGAS", "Es et al."),
    (2024, "Corr. RAG", "Yan et al."),
    (2025, "Agentic RAG", "Singh et al."),
    (2026, "RARE-RAG", "this work"),
]


# ── helpers ───────────────────────────────────────────────────────────────────
def draw_box(ax, cx, cy, label, sublabel, face, edge, bold=False):
    box = FBP(
        (cx - BOX_W, cy - BOX_H),
        2 * BOX_W,
        2 * BOX_H,
        boxstyle="round,pad=0.05",
        linewidth=0.8,
        edgecolor=edge,
        facecolor=face,
        zorder=2,
    )
    ax.add_patch(box)
    weight = "bold" if bold else "normal"
    ax.text(
        cx,
        cy + 0.12,
        label,
        ha="center",
        va="center",
        fontsize=7.5,
        fontweight=weight,
        zorder=3,
    )
    ax.text(
        cx,
        cy - 0.18,
        sublabel,
        ha="center",
        va="center",
        fontsize=6.0,
        color="#555555",
        zorder=3,
    )


def draw_year(ax, cx):
    box = FBP(
        (cx - YEAR_W, Y_AXIS - YEAR_H),
        2 * YEAR_W,
        2 * YEAR_H,
        boxstyle="round,pad=0.05",
        linewidth=0.8,
        edgecolor=YEAR_EDGE,
        facecolor=YEAR_FACE,
        zorder=4,
    )  # above the axis line
    ax.add_patch(box)
    year = int(round(cx / 2.0)) + 2020
    ax.text(
        cx,
        Y_AXIS,
        str(year),
        ha="center",
        va="center",
        fontsize=7.5,
        fontweight="bold",
        zorder=5,
    )


def vline(ax, x, y0, y1):
    ax.plot([x, x], [y0, y1], color=LINE_COL, linewidth=0.8, zorder=0)


# ── figure ────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(13, 5.0))
ax.set_xlim(-1.2, 13.5)
ax.set_ylim(-2.6, 4.2)
ax.set_aspect("equal")
ax.axis("off")

# timeline arrow — extends ~0.8 units past the 2026 box right edge (12.82)
ax.annotate(
    "",
    xy=(13.2, Y_AXIS),
    xytext=(-0.8, Y_AXIS),
    arrowprops=dict(arrowstyle="->", color="#888888", lw=1.2, zorder=1),
)

# year boxes
for y in YEARS:
    draw_year(ax, X[y])

# upper row 1
for yr, lbl, sub in upper1:
    draw_box(ax, X[yr], Y_UP1, lbl, sub, BLUE_FACE, BLUE_EDGE)

# upper row 2 (stacked)
for yr, lbl, sub in upper2:
    draw_box(ax, X[yr], Y_UP2, lbl, sub, BLUE_FACE, BLUE_EDGE)

# lower row
for yr, lbl, sub in lower:
    bold = lbl == "RARE-RAG"
    draw_box(ax, X[yr], Y_DN, lbl, sub, TEAL_FACE, TEAL_EDGE, bold=bold)

# ── connections ───────────────────────────────────────────────────────────────
# stacked chains: axis → row1 → row2
vline(ax, X[2020], Y_AXIS + YEAR_H, Y_UP1 - BOX_H)  # axis→RAG
vline(ax, X[2020], Y_UP1 + BOX_H, Y_UP2 - BOX_H)  # RAG→DPR

vline(ax, X[2024], Y_AXIS + YEAR_H, Y_UP1 - BOX_H)  # axis→GraphRAG
vline(ax, X[2024], Y_UP1 + BOX_H, Y_UP2 - BOX_H)  # GraphRAG→RAPTOR

# single upper connections
for yr in [2022, 2023, 2025, 2026]:
    vline(ax, X[yr], Y_AXIS + YEAR_H, Y_UP1 - BOX_H)

# lower connections
for yr in YEARS:
    vline(ax, X[yr], Y_AXIS - YEAR_H, Y_DN + BOX_H)

plt.tight_layout(pad=0)
plt.savefig("rag_timeline.png", dpi=150, bbox_inches="tight")
print("Saved rag_timeline.png")
