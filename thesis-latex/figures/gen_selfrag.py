"""Regenerate selfrag.png using matplotlib."""

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
PAD = 0.1  # rbox visual pad


# ── helpers ──────────────────────────────────────────────────────────────────
# rbox actual edges (FancyBboxPatch round,pad=PAD extends stated rect by PAD)
def rb(cx, w):
    return cx - w / 2 - PAD  # left


def rl(cx, w):
    return cx + w / 2 + PAD  # right


def rt(cy, h):
    return cy + h / 2 + PAD  # top


def rb_(cy, h):
    return cy - h / 2 - PAD  # bottom  (rb_ avoids name clash)


# diamond tips (exact polygon vertices)
def dt(cy, h):
    return cy + h / 2  # top tip  y


def db(cy, h):
    return cy - h / 2  # bottom tip y


def dr(cx, w):
    return cx + w / 2  # right tip x


def dl(cx, w):
    return cx - w / 2  # left tip  x


def rbox(ax, cx, cy, w, h, lines, face, edge, fs=10):
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
    ax.text(
        cx,
        cy,
        "\n".join(lines),
        ha="center",
        va="center",
        fontsize=fs,
        multialignment="center",
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


def diamond(ax, cx, cy, w, h, text, face, edge, fs=9.5):
    pts = [(cx, cy + h / 2), (cx + w / 2, cy), (cx, cy - h / 2), (cx - w / 2, cy)]
    ax.add_patch(
        plt.Polygon(
            pts,
            closed=True,
            linewidth=1.0,
            edgecolor=edge,
            facecolor=face,
            zorder=2,
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


def arr(ax, x0, y0, x1, y1, lbl="", lbl_dx=0.0, lbl_dy=0.18, lw=1.1, ls="solid"):
    ax.annotate(
        "",
        xy=(x1, y1),
        xytext=(x0, y0),
        arrowprops=dict(
            arrowstyle="-|>", color=ARROW, lw=lw, linestyle=ls, shrinkA=0, shrinkB=0
        ),
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
            fontsize=8.5,
            color=LCOLOR,
            style="italic",
        )


def line(ax, xs, ys):
    ax.plot(xs, ys, color=ARROW, lw=1.1, zorder=1)


def arrowhead(ax, x0, y0, x1, y1):
    """Single arrowhead at (x1,y1), no label."""
    ax.annotate(
        "",
        xy=(x1, y1),
        xytext=(x0, y0),
        arrowprops=dict(arrowstyle="-|>", color=ARROW, lw=1.1, shrinkA=0, shrinkB=0),
        zorder=2,
    )


def lbl(ax, x, y, text, rotation=0):
    ax.text(
        x,
        y,
        text,
        ha="center",
        va="center",
        fontsize=8.5,
        color=LCOLOR,
        style="italic",
        rotation=rotation,
    )


# ── canvas ────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(9.5, 11))
ax.set_xlim(0, 9.5)
ax.set_ylim(0, 11)
ax.axis("off")

# ── nodes ─────────────────────────────────────────────────────────────────────
#                cx    cy    w     h
ellipse(ax, 3.0, 10.0, 1.8, 0.65, "Query $q$", BLUE_F, BLUE_E)
diamond(ax, 3.0, 8.5, 2.4, 0.90, "[Retrieve?]", ORAN_F, ORAN_E)
rbox(ax, 6.0, 8.5, 1.9, 0.65, ["Retrieve", "passages"], BLUE_F, BLUE_E)
diamond(ax, 5.5, 6.8, 2.0, 0.85, "[IsRel?]", ORAN_F, ORAN_E)
rbox(ax, 8.0, 6.8, 1.6, 0.58, ["Discard", "passage"], RED_F, RED_E)
rbox(ax, 3.0, 5.1, 2.2, 0.65, ["Generate", "segment"], BLUE_F, BLUE_E)
diamond(ax, 3.0, 3.5, 2.2, 0.85, "[IsSup?]", ORAN_F, ORAN_E)
rbox(ax, 6.5, 3.5, 2.0, 0.65, ["Regenerate", "segment"], RED_F, RED_E)
diamond(ax, 3.0, 1.9, 2.2, 0.85, "[IsUse?]", ORAN_F, ORAN_E)
rbox(ax, 3.0, 0.5, 2.2, 0.62, ["Final answer $a$"], GREEN_F, GREEN_E)

# ── arrows ────────────────────────────────────────────────────────────────────
# Key coordinates:
#   Ellipse Query   cy=10.0 h=0.65 → bottom = 9.675
#   [Retrieve?]     cx=3.0  cy=8.5  w=2.4 h=0.90
#                     top=(3.0,8.95)  right=(4.2,8.5)  bottom=(3.0,8.05)  left=(1.8,8.5)
#   Retrieve pass.  cx=6.0  cy=8.5  w=1.9 h=0.65 → left=4.95  bottom=8.075
#   [IsRel?]        cx=5.5  cy=6.8  w=2.0 h=0.85
#                     top=(5.5,7.225) right=(6.5,6.8)  bottom=(5.5,6.375) left=(4.5,6.8)
#   Discard         cx=8.0  cy=6.8  w=1.6 h=0.58 → left=7.1
#   Generate seg.   cx=3.0  cy=5.1  w=2.2 h=0.65 → left=1.8  right=4.2  top=5.525  bottom=4.675
#   [IsSup?]        cx=3.0  cy=3.5  w=2.2 h=0.85
#                     top=(3.0,3.925) right=(4.1,3.5) bottom=(3.0,3.075)
#   Regenerate seg. cx=6.5  cy=3.5  w=2.0 h=0.65 → left=5.4  right=7.6
#   [IsUse?]        cx=3.0  cy=1.9  w=2.2 h=0.85
#                     top=(3.0,2.325) bottom=(3.0,1.475) left=(1.9,1.9)
#   Final answer    cx=3.0  cy=0.5  w=2.2 h=0.62 → top=0.91

# Query directly above [Retrieve?] → straight vertical down to top tip
arr(ax, 3.0, 9.675, 3.0, 8.95)

# [Retrieve?] right tip → Retrieve passages left edge
arr(ax, 4.2, 8.5, 4.95, 8.5, "yes", lbl_dy=0.19)

# Retrieve passages bottom → vertical down to [IsRel?] top y → horizontal left to top tip
line(ax, [6.0, 6.0], [8.075, 7.225])
arrowhead(ax, 6.0, 7.225, 5.5, 7.225)

# [IsRel?] right tip → Discard left edge
arr(ax, 6.5, 6.8, 7.1, 6.8, "not rel.", lbl_dy=0.20)

# [IsRel?] left tip (4.5,6.8) → horizontal left to x=3.0 → vertical down into Generate top (3.0,5.525)
line(ax, [4.5, 3.0, 3.0], [6.8, 6.8, 5.525])
arrowhead(ax, 3.0, 5.8, 3.0, 5.525)
lbl(ax, 3.75, 6.98, "relevant")

# [Retrieve?] no: BOTTOM tip (3.0,8.05) → down → left col x=0.85 → down → Generate left (1.8,5.1)
# Uses bottom vertex, leaving left vertex free for "not useful" — zero path overlap
line(ax, [3.0, 3.0, 0.85, 0.85, 1.8], [8.05, 7.4, 7.4, 5.1, 5.1])
arrowhead(ax, 1.4, 5.1, 1.8, 5.1)
lbl(ax, 2.1, 7.58, "no")

# Generate segment bottom → [IsSup?] top tip
arr(ax, 3.0, 4.675, 3.0, 3.925)

# [IsSup?] right tip → Regenerate segment left edge
arr(ax, 4.1, 3.5, 5.4, 3.5, "not sup.", lbl_dy=0.19)

# Regenerate retry: right edge (7.6,3.5) → (8.2,3.5) → (8.2,5.1) → Generate right edge (4.2,5.1)
line(ax, [7.6, 8.2, 8.2, 4.2], [3.5, 3.5, 5.1, 5.1])
arrowhead(ax, 4.6, 5.1, 4.2, 5.1)
lbl(ax, 7.0, 4.4, "retry")

# [IsSup?] bottom → [IsUse?] top
arr(ax, 3.0, 3.075, 3.0, 2.325, "supported", lbl_dx=0.60, lbl_dy=0.0)

# [IsUse?] bottom → Final answer top
arr(ax, 3.0, 1.475, 3.0, 0.91, "useful", lbl_dx=0.45, lbl_dy=0.0)

# [IsUse?] not useful: LEFT tip (1.9,1.9) → far-left col x=0.28 → up → [Retrieve?] LEFT tip (1.8,8.5)
# x=0.28 stays west of x=0.85 ("no" vertical), y=8.5 is above y=7.4 ("no" horizontal) — no crossing
line(ax, [1.9, 0.28, 0.28, 1.8], [1.9, 1.9, 8.5, 8.5])
arrowhead(ax, 1.4, 8.5, 1.8, 8.5)
lbl(ax, 0.10, 4.5, "not useful", rotation=90)

plt.tight_layout(pad=0.3)
plt.savefig("selfrag.png", dpi=200, bbox_inches="tight")
print("Saved selfrag.png")
