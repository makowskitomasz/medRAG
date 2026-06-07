"""Regenerate c4_container.png using matplotlib."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch as FBP

# ── colour palette ────────────────────────────────────────────────────────────
BLUE_F = "#dce6f7"
BLUE_E = "#6b8ec7"
ORAN_F = "#fdeac8"
ORAN_E = "#c07828"
GRAY_F = "#ebebeb"
GRAY_E = "#aaaaaa"
GRN_F = "#d5f0dc"
GRN_E = "#5aaa6a"
PINK_F = "#fde2ec"
PINK_E = "#cc5577"
DB_F = "#f0f0f0"
DB_E = "#999999"
ARROW = "#666666"


def rbox(ax, cx, cy, w, h, title, port="", face=BLUE_F, edge=BLUE_E, fs=8.5):
    p = FBP(
        (cx - w / 2, cy - h / 2),
        w,
        h,
        boxstyle="round,pad=0.07",
        linewidth=0.9,
        edgecolor=edge,
        facecolor=face,
        zorder=2,
    )
    ax.add_patch(p)
    if port:
        ax.text(
            cx,
            cy + 0.10,
            title,
            ha="center",
            va="center",
            fontsize=fs,
            fontweight="bold",
            zorder=3,
        )
        ax.text(
            cx,
            cy - 0.13,
            port,
            ha="center",
            va="center",
            fontsize=7.0,
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


def actor(ax, cx, cy, w, h, title, subtitle=""):
    p = FBP(
        (cx - w / 2, cy - h / 2),
        w,
        h,
        boxstyle="round,pad=0.07",
        linewidth=0.9,
        edgecolor=GRAY_E,
        facecolor=GRAY_F,
        zorder=2,
    )
    ax.add_patch(p)
    ax.text(
        cx,
        cy + 0.08,
        title,
        ha="center",
        va="center",
        fontsize=8.5,
        fontweight="bold",
        zorder=3,
    )
    if subtitle:
        ax.text(
            cx,
            cy - 0.13,
            subtitle,
            ha="center",
            va="center",
            fontsize=6.5,
            color="#666666",
            zorder=3,
        )


def cylinder(ax, cx, cy, w, h, label, sublabel=""):
    ew = w
    eh = 0.22
    body = FBP(
        (cx - w / 2, cy - h / 2),
        w,
        h,
        boxstyle="square,pad=0",
        linewidth=0.9,
        edgecolor=DB_E,
        facecolor=DB_F,
        zorder=2,
    )
    ax.add_patch(body)
    top = mpatches.Ellipse(
        (cx, cy + h / 2),
        ew,
        eh,
        linewidth=0.9,
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
        linewidth=0.9,
        edgecolor=DB_E,
        zorder=3,
    )
    ax.add_patch(bot)
    ax.text(
        cx,
        cy + 0.07,
        label,
        ha="center",
        va="center",
        fontsize=8.5,
        fontweight="bold",
        zorder=4,
    )
    if sublabel:
        ax.text(
            cx,
            cy - 0.14,
            sublabel,
            ha="center",
            va="center",
            fontsize=7.0,
            color="#555555",
            zorder=4,
        )


def group_box(ax, x0, y0, x1, y1, label, face="#f5f5ff", edge=BLUE_E, ls="dashed"):
    w = x1 - x0
    h = y1 - y0
    p = FBP(
        (x0, y0),
        w,
        h,
        boxstyle="round,pad=0.05",
        linewidth=1.0,
        edgecolor=edge,
        facecolor=face,
        linestyle=ls,
        zorder=1,
        alpha=0.5,
    )
    ax.add_patch(p)
    ax.text(
        (x0 + x1) / 2,
        y1 - 0.13,
        label,
        ha="center",
        va="top",
        fontsize=8,
        color=edge,
        fontweight="bold",
        zorder=2,
    )


def arr(ax, x0, y0, x1, y1, lbl="", dash=False, lw=0.9):
    ls = "--" if dash else "-"
    ax.annotate(
        "",
        xy=(x1, y1),
        xytext=(x0, y0),
        arrowprops=dict(arrowstyle="-|>", color=ARROW, lw=lw, linestyle=ls),
        zorder=1,
    )
    if lbl:
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        ax.text(
            mx + 0.05,
            my + 0.10,
            lbl,
            ha="center",
            va="center",
            fontsize=7,
            color="#777777",
            style="italic",
        )


# ── canvas ────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 14))
ax.set_xlim(0, 10)
ax.set_ylim(0, 14)
ax.axis("off")

# ── actors (top) ──────────────────────────────────────────────────────────────
actor(ax, 2.0, 13.2, 1.8, 0.60, "User", "REST / SSE")
actor(ax, 5.5, 13.2, 1.8, 0.60, "Admin User", "REST")

# ── api-gateway ───────────────────────────────────────────────────────────────
rbox(ax, 3.5, 12.0, 2.2, 0.58, "api-gateway", ":8000")

# ── auth ──────────────────────────────────────────────────────────────────────
rbox(ax, 7.0, 12.0, 1.8, 0.58, "auth", ":8001")

# ── Query Pipeline group ──────────────────────────────────────────────────────
group_box(ax, 0.5, 7.8, 4.5, 11.4, "Query Pipeline", face="#f0f4ff", edge=BLUE_E)

QX = 2.5
for i, (svc, port) in enumerate(
    [
        ("orchestrator", ":8002"),
        ("query-processor", ":8003"),
        ("retrieval", ":8004"),
        ("reranker", ":8005"),
        ("generation", ":8006"),
    ]
):
    y = 11.0 - i * 0.68
    rbox(ax, QX, y, 2.8, 0.52, svc, port)

# ── Ingestion Pipeline group ──────────────────────────────────────────────────
group_box(ax, 5.3, 7.8, 9.5, 11.4, "Ingestion Pipeline", face="#fff8f0", edge=ORAN_E)

IX = 7.4
rbox(ax, IX, 11.0, 2.2, 0.52, "ingestion", ":8007")
rbox(ax, IX, 10.3, 2.2, 0.52, "RabbitMQ broker", "async events", ORAN_F, ORAN_E)
for i, (svc, port) in enumerate(
    [
        ("parser", ":8008"),
        ("chunking", ":8009"),
        ("embedding", ":8010"),
        ("indexing", ":8011"),
    ]
):
    y = 9.6 - i * 0.60
    rbox(ax, IX, y, 2.2, 0.48, svc, port)

# ── admin + eval ──────────────────────────────────────────────────────────────
rbox(ax, 2.0, 7.1, 2.2, 0.52, "admin", ":8012")
rbox(ax, 5.0, 7.1, 2.2, 0.52, "eval", ":8013")

# ── Infrastructure ────────────────────────────────────────────────────────────
group_box(
    ax,
    0.5,
    5.0,
    9.5,
    6.6,
    "Infrastructure",
    face="#f5f5f5",
    edge="#999999",
    ls="dashed",
)

cylinder(ax, 2.0, 5.8, 2.0, 0.72, "MongoDB", ":27017")
cylinder(ax, 5.0, 5.8, 2.0, 0.72, "Weaviate", ":8080")
cylinder(ax, 8.0, 5.8, 2.0, 0.72, "RabbitMQ", ":5672")

# ── External APIs ─────────────────────────────────────────────────────────────
group_box(
    ax, 0.5, 2.8, 9.5, 4.4, "External APIs", face="#fff0f5", edge=PINK_E, ls="dashed"
)

rbox(ax, 2.8, 3.6, 3.0, 0.80, "Anthropic LLM", "claude-sonnet-4-6", PINK_F, PINK_E)
rbox(ax, 7.2, 3.6, 3.0, 0.80, "Embedding Provider", "BGE-M3 / Cohere", PINK_F, PINK_E)

# ── Arrows ────────────────────────────────────────────────────────────────────
# User → api-gateway
arr(ax, 2.0, 12.90, 2.8, 12.29)
# Admin → api-gateway
arr(ax, 5.5, 12.90, 4.6, 12.29)
# api-gateway → auth (JWT check dashed)
arr(ax, 4.60, 12.00, 6.10, 12.00, "JWT check", dash=True)
# api-gateway → orchestrator
arr(ax, 3.5, 11.71, 2.8, 11.24, "query")
# api-gateway → ingestion
arr(ax, 4.40, 11.71, 6.30, 11.24, "upload")
# orchestrator → query-processor
arr(ax, 2.5, 10.74, 2.5, 10.56)
# query-processor → retrieval
arr(ax, 2.5, 10.08, 2.5, 9.90)
# retrieval → reranker
arr(ax, 2.5, 9.42, 2.5, 9.24)
# reranker → generation
arr(ax, 2.5, 8.76, 2.5, 8.58)
# ingestion → RabbitMQ broker
arr(ax, 7.4, 10.74, 7.4, 10.56)
# RabbitMQ broker → parser
arr(ax, 7.4, 10.08, 7.4, 9.90)
# parser → chunking
arr(ax, 7.4, 9.42, 7.4, 9.24)
# chunking → embedding
arr(ax, 7.4, 8.76, 7.4, 8.58)
# embedding → indexing
arr(ax, 7.4, 8.10, 7.4, 7.92)
# query pipeline → MongoDB
arr(ax, 2.5, 7.80, 2.0, 6.16)
# indexing → Weaviate
arr(ax, 7.4, 7.54, 5.2, 6.16)
# ingestion → MongoDB
arr(ax, 6.30, 11.00, 2.8, 6.16, dash=True)
# generation → Anthropic
arr(ax, 2.5, 8.32, 2.2, 4.00, dash=True)
# embedding → Embedding Provider
arr(ax, 7.4, 7.80, 6.6, 4.00, dash=True)

plt.tight_layout(pad=0.2)
plt.savefig("c4_container.png", dpi=200, bbox_inches="tight")
print("Saved c4_container.png")
