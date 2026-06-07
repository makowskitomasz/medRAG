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


def rbox(ax, cx, cy, w, h, lines, face, edge, fs=10):
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
    e = mpatches.Ellipse(
        (cx, cy), w, h, linewidth=1.0, edgecolor=edge, facecolor=face, zorder=2
    )
    ax.add_patch(e)
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fs, zorder=3)


def diamond(ax, cx, cy, w, h, text, face, edge, fs=9.5):
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


def arr(
    ax,
    x0,
    y0,
    x1,
    y1,
    lbl="",
    lbl_dx=0.0,
    lbl_dy=0.18,
    style="-|>",
    lw=1.1,
    ls="solid",
    conn=None,
):
    kw = dict(arrowstyle=style, color=ARROW, lw=lw, linestyle=ls)
    if conn:
        kw["connectionstyle"] = conn
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=kw, zorder=1)
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


# ── canvas ────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(9.5, 11))
ax.set_xlim(0, 9.5)
ax.set_ylim(0, 11)
ax.axis("off")

# ── nodes ─────────────────────────────────────────────────────────────────────
# Query q (top)
ellipse(ax, 4.0, 10.0, 1.8, 0.65, "Query $q$", BLUE_F, BLUE_E)

# [Retrieve?] diamond
diamond(ax, 3.0, 8.5, 2.4, 0.90, "[Retrieve?]", ORAN_F, ORAN_E)

# Retrieve passages (right of diamond)
rbox(ax, 6.0, 8.5, 1.9, 0.65, ["Retrieve", "passages"], BLUE_F, BLUE_E)

# [IsRel?] diamond
diamond(ax, 5.5, 6.8, 2.0, 0.85, "[IsRel?]", ORAN_F, ORAN_E)

# Discard passage (right)
rbox(ax, 8.0, 6.8, 1.6, 0.58, ["Discard", "passage"], RED_F, RED_E)

# Generate segment (middle)
rbox(ax, 3.0, 5.1, 2.2, 0.65, ["Generate", "segment"], BLUE_F, BLUE_E)

# [IsSup?] diamond
diamond(ax, 3.0, 3.5, 2.2, 0.85, "[IsSup?]", ORAN_F, ORAN_E)

# Regenerate segment (right)
rbox(ax, 6.5, 3.5, 2.0, 0.65, ["Regenerate", "segment"], RED_F, RED_E)

# [IsUse?] diamond
diamond(ax, 3.0, 1.9, 2.2, 0.85, "[IsUse?]", ORAN_F, ORAN_E)

# Final answer (bottom)
rbox(ax, 3.0, 0.5, 2.2, 0.62, ["Final answer $a$"], GREEN_F, GREEN_E)

# ── arrows ────────────────────────────────────────────────────────────────────
# Query → Retrieve?
arr(ax, 4.0, 9.68, 3.3, 8.95)

# Retrieve? yes → Retrieve passages
arr(ax, 4.20, 8.50, 5.05, 8.50, "yes", lbl_dy=0.19, lbl_dx=0.0)

# Retrieve passages → IsRel?
arr(ax, 6.0, 8.17, 5.8, 7.22)

# IsRel? not rel → Discard
arr(ax, 6.50, 6.80, 7.20, 6.80, "not rel.", lbl_dy=0.20)

# IsRel? relevant → Generate segment (diagonal)
arr(ax, 4.50, 6.60, 3.50, 5.42, "relevant", lbl_dx=-0.5, lbl_dy=0.0)

# Retrieve? no → Generate segment
arr(ax, 1.80, 8.50, 1.0, 8.50, lbl="", lbl_dy=0)
ax.annotate(
    "",
    xy=(1.0, 5.10),
    xytext=(1.0, 8.50),
    arrowprops=dict(arrowstyle="-|>", color=ARROW, lw=1.1),
    zorder=1,
)
arr(ax, 1.0, 5.10, 1.90, 5.10, "no", lbl_dy=0.19)

# Generate segment → IsSup?
arr(ax, 3.0, 4.77, 3.0, 3.92)

# IsSup? not sup → Regenerate
arr(ax, 4.10, 3.50, 5.50, 3.50, "not sup.", lbl_dy=0.19)

# Regenerate → retry → Generate segment (loop right side)
ax.plot([7.5, 8.2, 8.2, 4.1], [3.5, 3.5, 5.1, 5.1], color=ARROW, lw=1.1, zorder=1)
ax.annotate(
    "",
    xy=(4.1, 5.1),
    xytext=(4.3, 5.1),
    arrowprops=dict(arrowstyle="-|>", color=ARROW, lw=1.1),
    zorder=2,
)
ax.text(
    6.8,
    4.35,
    "retry",
    ha="center",
    va="center",
    fontsize=8.5,
    color=LCOLOR,
    style="italic",
)

# IsSup? supported → IsUse?
arr(ax, 3.0, 3.07, 3.0, 2.33, "supported", lbl_dx=0.55, lbl_dy=0.0)

# IsUse? useful → Final answer
arr(ax, 3.0, 1.47, 3.0, 0.81, "useful", lbl_dx=0.45, lbl_dy=0.0)

# IsUse? not useful → loop back left → [Retrieve?]
# left edge of [IsUse?]: 3.0-1.1=1.9, left edge of [Retrieve?]: 3.0-1.2=1.8
ax.plot([1.9, 0.6, 0.6, 1.8], [1.9, 1.9, 8.5, 8.5], color=ARROW, lw=1.1, zorder=1)
ax.annotate(
    "",
    xy=(1.8, 8.5),
    xytext=(1.6, 8.5),
    arrowprops=dict(arrowstyle="-|>", color=ARROW, lw=1.1),
    zorder=2,
)
ax.text(
    0.25,
    5.2,
    "not useful",
    ha="center",
    va="center",
    fontsize=8.5,
    color=LCOLOR,
    style="italic",
    rotation=90,
)

plt.tight_layout(pad=0.3)
plt.savefig("selfrag.png", dpi=200, bbox_inches="tight")
print("Saved selfrag.png")
