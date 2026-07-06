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

HEAD_LEN = 0.08  # arrowhead length in data units
HEAD_W = 0.05  # arrowhead half-width in data units


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
ax.set_xlim(-0.3, 9.0)  # symmetric around content centre ≈ 4.35
ax.set_ylim(0.2, 6.8)
ax.axis("off")

# Column centres:  C1=1.0  C2=4.4  C3=7.8   (spacing +3.4 each)
# All rbox edges extended by pad=0.08; cylinder uses square,pad=0.
PAD = 0.08

# ── boxes ────────────────────────────────────────────────────────────────────
rbox(ax, 1.0, 5.4, 1.6, 0.62, ["Query $q$"], BLUE_F, BLUE_E)
rbox(ax, 4.4, 5.4, 2.0, 0.70, ["Retriever", "$E_Q(q)$"], BLUE_F, BLUE_E)
cylinder(ax, 7.8, 5.35, 1.6, 0.80, ["Vector", "Index"])

rbox(ax, 1.0, 3.0, 1.7, 0.70, ["LLM", "Generator"], RED_F, RED_E)
rbox(ax, 4.4, 3.0, 2.2, 0.72, ["Prompt", r"$[q;\,d_1;\,\ldots;\,d_k]$"], ORAN_F, ORAN_E)
rbox(ax, 7.8, 3.0, 1.7, 0.62, ["Top-$k$", "Passages"], GREEN_F, GREEN_E)

rbox(ax, 1.0, 1.0, 1.6, 0.62, ["Answer $a$"], BLUE_F, BLUE_E)

# ── arrows ───────────────────────────────────────────────────────────────────
# Query right (1.0+0.8+PAD=1.88) → Retriever left (4.4-1.0-PAD=3.32)
arr(ax, 1.88, 5.40, 3.32, 5.40)
lbl(ax, 2.60, 5.57, "embed")

# Retriever right (4.4+1.0+PAD=5.48) → Cylinder left (7.8-0.8=7.00, pad=0)
arr(ax, 5.48, 5.40, 7.00, 5.40)
lbl(ax, 6.24, 5.57, "ANN search")

# Cylinder bottom (5.35-0.40=4.95) → Top-k top (3.0+0.31+PAD=3.39)
arr(ax, 7.80, 4.95, 7.80, 3.39)

# Top-k left (7.8-0.85-PAD=6.87) → Prompt right (4.4+1.1+PAD=5.58)
arr(ax, 6.87, 3.00, 5.58, 3.00)
lbl(ax, 6.22, 3.17, "concatenate")

# Prompt left (4.4-1.1-PAD=3.22) → LLM right (1.0+0.85+PAD=1.93)
arr(ax, 3.22, 3.00, 1.93, 3.00)
lbl(ax, 2.57, 3.17, "condition")

# LLM bottom (3.0-0.35-PAD=2.57) → Answer top (1.0+0.31+PAD=1.39)
arr(ax, 1.00, 2.57, 1.00, 1.39)

plt.savefig("vanilla_rag.png", dpi=200, bbox_inches="tight")
print("Saved vanilla_rag.png")
