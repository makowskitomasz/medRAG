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
GRAY_F = "#ebebeb"
GRAY_E = "#aaaaaa"
DB_F = "#f0f0f0"
DB_E = "#999999"
ARROW = "#555555"


def rbox(ax, cx, cy, w, h, title, port="", face=BLUE_F, edge=BLUE_E, fs=9.5):
    p = FBP(
        (cx - w / 2, cy - h / 2),
        w,
        h,
        boxstyle="round,pad=0.10",
        linewidth=1.0,
        edgecolor=edge,
        facecolor=face,
        zorder=2,
    )
    ax.add_patch(p)
    if port:
        ax.text(
            cx,
            cy + 0.12,
            title,
            ha="center",
            va="center",
            fontsize=fs,
            fontweight="bold",
            zorder=3,
        )
        ax.text(
            cx,
            cy - 0.14,
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
            zorder=3,
        )


def cylinder(ax, cx, cy, w, h, label, sublabel=""):
    ew = w
    eh = 0.25
    body = FBP(
        (cx - w / 2, cy - h / 2),
        w,
        h,
        boxstyle="square,pad=0",
        linewidth=1.0,
        edgecolor=DB_E,
        facecolor=DB_F,
        zorder=2,
    )
    ax.add_patch(body)
    top = mpatches.Ellipse(
        (cx, cy + h / 2),
        ew,
        eh,
        linewidth=1.0,
        edgecolor=DB_E,
        facecolor=DB_F,
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
        edgecolor=DB_E,
        zorder=3,
    )
    ax.add_patch(bot)
    ax.text(
        cx,
        cy + 0.08,
        label,
        ha="center",
        va="center",
        fontsize=9.5,
        fontweight="bold",
        zorder=4,
    )
    if sublabel:
        ax.text(
            cx,
            cy - 0.16,
            sublabel,
            ha="center",
            va="center",
            fontsize=7.5,
            color="#555555",
            zorder=4,
        )


def arr(ax, x0, y0, x1, y1, lbl="", lbl_dy=0.17, lbl_dx=0.0, mono=False, lw=1.1):
    ax.annotate(
        "",
        xy=(x1, y1),
        xytext=(x0, y0),
        arrowprops=dict(arrowstyle="-|>", color=ARROW, lw=lw),
        zorder=1,
    )
    if lbl:
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        ff = "monospace" if mono else "sans-serif"
        ax.text(
            mx + lbl_dx,
            my + lbl_dy,
            lbl,
            ha="center",
            va="center",
            fontsize=8.0,
            color="#666666",
            fontfamily=ff,
        )


# ── canvas ────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(13, 6.5))
ax.set_xlim(0, 13)
ax.set_ylim(0, 6.5)
ax.axis("off")

# ── Row 1: ingestion pipeline (top, left → right) ─────────────────────────────
Y1 = 5.0
rbox(ax, 1.5, Y1, 2.0, 0.72, "Ingestion", ":8007")
rbox(ax, 4.0, Y1, 2.0, 0.72, "RabbitMQ\nbroker", "", ORAN_F, ORAN_E)
rbox(ax, 6.8, Y1, 2.0, 0.72, "Parser", ":8008")
rbox(ax, 9.8, Y1, 2.0, 0.72, "Chunking", ":8009")

# ── Row 2: embedding + indexing (bottom-right) ────────────────────────────────
Y2 = 2.6
rbox(ax, 9.8, Y2, 2.0, 0.72, "Embedding", ":8010")
rbox(ax, 7.0, Y2, 2.0, 0.72, "Indexing", ":8011")

# ── Databases ─────────────────────────────────────────────────────────────────
cylinder(ax, 1.8, 1.5, 2.0, 0.90, "MongoDB")
cylinder(ax, 7.0, 0.6, 2.0, 0.90, "Weaviate")

# ── Arrows row 1 ─────────────────────────────────────────────────────────────
arr(ax, 2.50, Y1, 3.00, Y1, "file.uploaded", lbl_dy=0.20, mono=True)
arr(ax, 5.00, Y1, 5.80, Y1, "consume", lbl_dy=0.20)
arr(ax, 7.80, Y1, 8.80, Y1, "file.parsed", lbl_dy=0.20, mono=True)

# Chunking → down-right bend → Embedding (with label chunks.created)
ax.annotate(
    "",
    xy=(9.8, Y2 + 0.36),
    xytext=(9.8, Y1 - 0.36),
    arrowprops=dict(
        arrowstyle="-|>", color=ARROW, lw=1.1, connectionstyle="arc3,rad=0.0"
    ),
    zorder=1,
)
ax.text(
    10.4,
    (Y1 + Y2) / 2,
    "chunks\n.created",
    ha="left",
    va="center",
    fontsize=7.5,
    color="#666666",
    fontfamily="monospace",
)

# Embedding ← Indexing
arr(ax, 9.8, Y2, 8.00, Y2, "embeddings.ready", lbl_dy=0.20, mono=True)

# ── Arrows: ingestion → MongoDB ───────────────────────────────────────────────
arr(ax, 1.5, Y1 - 0.36, 1.8, 2.45, "dedup check", lbl_dy=0.0, lbl_dx=0.6)

# Indexing → MongoDB (update status)
ax.annotate(
    "",
    xy=(1.8, 1.95),
    xytext=(6.0, 2.20),
    arrowprops=dict(
        arrowstyle="-|>", color=ARROW, lw=1.1, connectionstyle="arc3,rad=0.1"
    ),
    zorder=1,
)
ax.text(
    3.8, 2.5, "update status", ha="center", va="center", fontsize=8.0, color="#666666"
)

# Indexing → Weaviate
arr(ax, 7.0, Y2 - 0.36, 7.0, 1.05, "upsert vectors", lbl_dy=0.0, lbl_dx=0.7)

plt.tight_layout(pad=0.3)
plt.savefig("seq_ingestion.png", dpi=200, bbox_inches="tight")
print("Saved seq_ingestion.png")
