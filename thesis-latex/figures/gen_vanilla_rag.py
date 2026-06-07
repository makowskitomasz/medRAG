"""Regenerate vanilla_rag.png using matplotlib."""

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
ORAN_F = "#fde8cc"
ORAN_E = "#d08040"
GRAY_F = "#ebebeb"
GRAY_E = "#aaaaaa"
ARROW = "#555555"

HEAD_LEN = 0.14  # arrowhead length in data units
HEAD_W = 0.09  # arrowhead half-width in data units


def rbox(ax, cx, cy, w, h, lines, face, edge, fs=10):
    p = FBP(
        (cx - w / 2, cy - h / 2),
        w,
        h,
        boxstyle="round,pad=0.08",
        linewidth=1.0,
        edgecolor=edge,
        facecolor=face,
        zorder=2,
    )
    ax.add_patch(p)
    text = "\n".join(lines)
    ax.text(
        cx,
        cy,
        text,
        ha="center",
        va="center",
        fontsize=fs,
        multialignment="center",
        fontfamily="DejaVu Sans",
        zorder=3,
    )


def cylinder(ax, cx, cy, w, h, lines):
    ew = w
    eh = 0.28
    body = FBP(
        (cx - w / 2, cy - h / 2),
        w,
        h,
        boxstyle="square,pad=0",
        linewidth=1.0,
        edgecolor=GRAY_E,
        facecolor=GRAY_F,
        zorder=2,
    )
    ax.add_patch(body)
    top = mpatches.Ellipse(
        (cx, cy + h / 2),
        ew,
        eh,
        linewidth=1.0,
        edgecolor=GRAY_E,
        facecolor=GRAY_F,
        zorder=3,
    )
    ax.add_patch(top)
    bot = mpatches.Arc(
        (cx, cy - h / 2),
        ew,
        eh,
        theta1=180,
        theta2=360,
        linewidth=1.0,
        edgecolor=GRAY_E,
        zorder=3,
    )
    ax.add_patch(bot)
    text = "\n".join(lines)
    ax.text(
        cx,
        cy,
        text,
        ha="center",
        va="center",
        fontsize=10,
        multialignment="center",
        zorder=4,
    )


def arr(ax, x0, y0, x1, y1):
    """Arrow with tip precisely at (x1,y1): shaft via plot + filled polygon head."""
    dx, dy = x1 - x0, y1 - y0
    length = (dx**2 + dy**2) ** 0.5
    ux, uy = dx / length, dy / length  # unit vector
    px, py = -uy, ux  # perpendicular
    bx = x1 - ux * HEAD_LEN  # arrowhead base centre
    by = y1 - uy * HEAD_LEN
    ax.plot([x0, bx], [y0, by], color=ARROW, lw=1.1, zorder=4, solid_capstyle="butt")
    tri = plt.Polygon(
        [
            (x1, y1),
            (bx + px * HEAD_W, by + py * HEAD_W),
            (bx - px * HEAD_W, by - py * HEAD_W),
        ],
        closed=True,
        facecolor=ARROW,
        edgecolor=ARROW,
        zorder=4,
    )
    ax.add_patch(tri)


def lbl(ax, x, y, text):
    ax.text(
        x,
        y,
        text,
        ha="center",
        va="center",
        fontsize=8,
        color="#666666",
        style="italic",
        zorder=5,
    )


fig, ax = plt.subplots(figsize=(9, 7))
ax.set_xlim(0.3, 8.8)
ax.set_ylim(0.2, 6.8)
ax.axis("off")

# ── boxes ────────────────────────────────────────────────────────────────────
# Row 1 (y=5.4):  Query | Retriever | Vector Index
#   Query:     cx=1.4, w=1.6  → right=2.20
#   Retriever: cx=4.1, w=2.0  → left=3.10, right=5.10
#   Cylinder:  cx=7.0, w=1.6  → left=6.20, bottom=4.95
rbox(ax, 1.4, 5.4, 1.6, 0.62, ["Query $q$"], BLUE_F, BLUE_E)
rbox(ax, 4.1, 5.4, 2.0, 0.70, ["Retriever", "$E_Q(q)$"], BLUE_F, BLUE_E)
cylinder(ax, 7.0, 5.35, 1.6, 0.80, ["Vector", "Index"])

# Row 2 (y=3.0):  LLM Generator | Prompt | Top-k Passages
#   LLM:    cx=1.4, w=1.7  → right=2.25, bottom=2.65
#   Prompt: cx=4.1, w=2.2  → left=3.00, right=5.20
#   Top-k:  cx=7.0, w=1.7  → left=6.15, top=3.31
rbox(ax, 1.4, 3.0, 1.7, 0.70, ["LLM", "Generator"], RED_F, RED_E)
rbox(ax, 4.1, 3.0, 2.2, 0.72, ["Prompt", r"$[q;\,d_1;\,\ldots;\,d_k]$"], ORAN_F, ORAN_E)
rbox(ax, 7.0, 3.0, 1.7, 0.62, ["Top-$k$", "Passages"], GREEN_F, GREEN_E)

# Row 3 (y=1.0):  Answer
#   Answer: cx=1.4, w=1.6  → top=1.31
rbox(ax, 1.4, 1.0, 1.6, 0.62, ["Answer $a$"], BLUE_F, BLUE_E)

# ── arrows ───────────────────────────────────────────────────────────────────
arr(ax, 2.20, 5.40, 3.10, 5.40)  # Query right → Retriever left
lbl(ax, 2.65, 5.57, "embed")

arr(ax, 5.10, 5.40, 6.20, 5.40)  # Retriever right → Cylinder left (6.20)
lbl(ax, 5.65, 5.57, "ANN search")

arr(ax, 7.00, 4.95, 7.00, 3.31)  # Cylinder bottom (4.95) → Top-k top (3.31)

arr(ax, 6.15, 3.00, 5.20, 3.00)  # Top-k left → Prompt right
lbl(ax, 5.67, 3.17, "concatenate")

arr(ax, 3.00, 3.00, 2.25, 3.00)  # Prompt left → LLM right
lbl(ax, 2.62, 3.17, "condition")

arr(ax, 1.40, 2.65, 1.40, 1.31)  # LLM bottom → Answer top

plt.savefig("vanilla_rag.png", dpi=200, bbox_inches="tight")
print("Saved vanilla_rag.png")
