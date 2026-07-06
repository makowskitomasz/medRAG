"""Regenerate seq_ingestion.png — ingestion pipeline flow using matplotlib."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch as FBP

BLUE_F = "#dce6f7"
BLUE_E = "#6b8ec7"
ORAN_F = "#fdeac8"
ORAN_E = "#c07828"
DB_F = "#f0f0f0"
DB_E = "#999999"
ARROW = "#555555"
PAD = 0.10
W = 2.2  # box width
H = 0.85  # box height


def rbox(ax, cx, cy, title, port="", face=BLUE_F, edge=BLUE_E, fs=9.5):
    ax.add_patch(
        FBP(
            (cx - W / 2, cy - H / 2),
            W,
            H,
            boxstyle=f"round,pad={PAD}",
            linewidth=1.0,
            edgecolor=edge,
            facecolor=face,
            zorder=2,
        )
    )
    if port:
        ax.text(
            cx,
            cy + 0.13,
            title,
            ha="center",
            va="center",
            fontsize=fs,
            fontweight="bold",
            zorder=3,
        )
        ax.text(
            cx,
            cy - 0.16,
            port,
            ha="center",
            va="center",
            fontsize=7.5,
            color="#555555",
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
            multialignment="center",
            zorder=3,
        )


def cylinder(ax, cx, cy, label):
    cw, ch = 2.2, 0.90
    ax.add_patch(
        FBP(
            (cx - cw / 2, cy - ch / 2),
            cw,
            ch,
            boxstyle="square,pad=0",
            linewidth=1.0,
            edgecolor=DB_E,
            facecolor=DB_F,
            zorder=2,
        )
    )
    ax.add_patch(
        mpatches.Ellipse(
            (cx, cy + ch / 2),
            cw,
            0.26,
            linewidth=1.0,
            edgecolor=DB_E,
            facecolor=DB_F,
            zorder=3,
        )
    )
    ax.add_patch(
        mpatches.Arc(
            (cx, cy - ch / 2),
            cw,
            0.26,
            theta1=180,
            theta2=360,
            linewidth=1.0,
            edgecolor=DB_E,
            zorder=3,
        )
    )
    ax.text(
        cx,
        cy,
        label,
        ha="center",
        va="center",
        fontsize=9.5,
        fontweight="bold",
        zorder=4,
    )


def arr(ax, x0, y0, x1, y1, lbl="", lbl_dy=0.23, lbl_dx=0.0, mono=False, lw=1.1):
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
            fontsize=8.0,
            color="#666666",
            fontfamily="monospace" if mono else "sans-serif",
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


def lbl(ax, x, y, text, ha="center", mono=False):
    ax.text(
        x,
        y,
        text,
        ha=ha,
        va="center",
        fontsize=8.0,
        color="#666666",
        fontfamily="monospace" if mono else "sans-serif",
    )


# ── canvas ────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(14, 9))
ax.set_xlim(0, 14)
ax.set_ylim(0, 9)
ax.axis("off")

Y1 = 7.5  # row 1: pipeline services
Y2 = 5.0  # row 2: embedding + indexing
YDB = 2.2  # databases

# ── layout & actual edges  (cx ± W/2 ± PAD  =  cx ± 1.2)
# 4 boxes × 2.4 + 3 gaps × 1.2 = 13.2 → centered in 14: margin 0.4 each side
# Row 1  cx:  1.6   5.2   8.8   12.4    gaps = 1.2 between actual edges
# Ingestion  left=0.4  right=2.8  bottom=6.975
# RabbitMQ   left=4.0  right=6.4
# Parser     left=7.6  right=10.0
# Chunking   left=11.2 right=13.6 bottom=6.975
#
# Row 2  cx:  8.8 (Indexing)   12.4 (Embedding)
# Embedding  left=11.2 right=13.6 top=5.525 bottom=4.475
# Indexing   left=7.6  right=10.0 top=5.525 bottom=4.475
#
# MongoDB    cx=1.6  cy=2.2  top_cap = 2.2+0.45+0.13 = 2.78
# Weaviate   cx=6.5  cy=2.2  top_cap = 2.78

TOP_CAP = YDB + 0.45 + 0.13  # ≈ 2.78

# ── nodes ────────────────────────────────────────────────────────────────────
rbox(ax, 1.6, Y1, "Ingestion", ":8007")
rbox(ax, 5.2, Y1, "RabbitMQ\nbroker", "", ORAN_F, ORAN_E)
rbox(ax, 8.8, Y1, "Parser", ":8008")
rbox(ax, 12.4, Y1, "Chunking", ":8009")
rbox(ax, 12.4, Y2, "Embedding", ":8010")
rbox(ax, 8.8, Y2, "Indexing", ":8011")
cylinder(ax, 1.6, YDB, "MongoDB")
cylinder(ax, 6.5, YDB, "Weaviate")

# ── arrows ────────────────────────────────────────────────────────────────────

# Row 1 horizontal pipeline
arr(ax, 2.8, Y1, 4.0, Y1, "file.uploaded", lbl_dy=0.24, mono=True)
arr(ax, 6.4, Y1, 7.6, Y1, "consume", lbl_dy=0.24)
arr(ax, 10.0, Y1, 11.2, Y1, "file.parsed", lbl_dy=0.24, mono=True)

# Chunking → Embedding  (straight vertical)
arr(ax, 12.4, 6.975, 12.4, 5.525)
lbl(ax, 12.58, 6.25, "chunks.created", ha="left", mono=True)

# Embedding → Indexing  (horizontal left)
arr(ax, 11.2, Y2, 10.0, Y2, "embeddings.ready", lbl_dy=0.24, mono=True)

# Ingestion → MongoDB  (straight vertical, dedup check)
# Ingestion bottom=6.975 → MongoDB top_cap
line(ax, [1.6, 1.6], [6.975, TOP_CAP])
arrowhead(ax, 1.6, 3.1, 1.6, TOP_CAP)
lbl(ax, 1.78, 4.85, "dedup check", ha="left")

# Indexing → MongoDB  (exit left → down at x=4.5 → right-to-left into MongoDB side)
# x=4.5 is between Weaviate left (5.4) and MongoDB right (2.7) — vertical clears both cylinders
line(ax, [7.6, 4.5, 4.5, 2.7], [5.35, 5.35, 2.2, 2.2])
arrowhead(ax, 3.1, 2.2, 2.7, 2.2)
lbl(ax, 4.7, 3.78, "update status", ha="left")

# Indexing → Weaviate  (exit left side at y=5.15 → left to Weaviate cx=6.5 → down into top cap)
line(ax, [7.6, 6.5, 6.5], [5.15, 5.15, TOP_CAP])
arrowhead(ax, 6.5, 3.1, 6.5, TOP_CAP)
lbl(ax, 6.68, 3.95, "upsert\nvectors", ha="left")

plt.tight_layout(pad=0.3)
plt.savefig("seq_ingestion.png", dpi=200, bbox_inches="tight")
print("Saved seq_ingestion.png")
