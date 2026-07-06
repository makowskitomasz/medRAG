"""Regenerate c4_context.png using matplotlib."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch as FBP

BLUE_F = "#dce6f7"
BLUE_E = "#6b8ec7"
PINK_F = "#fde2ec"
PINK_E = "#cc5577"
GRAY_F = "#ebebeb"
GRAY_E = "#aaaaaa"
ARROW = "#888888"


def rbox(ax, cx, cy, w, h, lines, face, edge, fs=10, linestyle="solid"):
    p = FBP(
        (cx - w / 2, cy - h / 2),
        w,
        h,
        boxstyle="round,pad=0.12",
        linewidth=1.2,
        edgecolor=edge,
        facecolor=face,
        linestyle=linestyle,
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
        zorder=3,
    )


def arr(ax, x0, y0, x1, y1, lbl=""):
    ax.annotate(
        "",
        xy=(x1, y1),
        xytext=(x0, y0),
        arrowprops=dict(arrowstyle="-|>", color=ARROW, lw=1.1),
        zorder=1,
    )
    if lbl:
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        ax.text(
            mx, my + 0.15, lbl, ha="center", va="center", fontsize=8.5, color="#666666"
        )


fig, ax = plt.subplots(figsize=(12, 5))
ax.set_xlim(-0.7, 12.7)
ax.set_ylim(0.2, 5.3)
ax.axis("off")

# ── Central platform box ──────────────────────────────────────────────────────
cx_plat = 6.0
cy_plat = 2.75
pw, ph = 5.4, 3.0

p = FBP(
    (cx_plat - pw / 2, cy_plat - ph / 2),
    pw,
    ph,
    boxstyle="round,pad=0.15",
    linewidth=2.0,
    edgecolor=BLUE_E,
    facecolor=BLUE_F,
    zorder=2,
)
ax.add_patch(p)

ax.text(
    cx_plat,
    cy_plat + 0.85,
    "medRAG Platform",
    ha="center",
    va="center",
    fontsize=13,
    fontweight="bold",
    color=BLUE_E,
    style="italic",
    fontfamily="DejaVu Serif",
    zorder=3,
)
ax.text(
    cx_plat,
    cy_plat + 0.22,
    "14 microservices",
    ha="center",
    va="center",
    fontsize=10,
    zorder=3,
)
ax.text(
    cx_plat,
    cy_plat - 0.22,
    "FastAPI + Weaviate + MongoDB",
    ha="center",
    va="center",
    fontsize=10,
    zorder=3,
)
ax.text(
    cx_plat,
    cy_plat - 0.65,
    "RabbitMQ ingestion pipeline",
    ha="center",
    va="center",
    fontsize=10,
    zorder=3,
)

# ── Left actors ───────────────────────────────────────────────────────────────
# Patient/User (top-left)
rbox(
    ax,
    0.85,
    3.6,
    2.2,
    0.82,
    ["Patient / User", "queries drug interactions"],
    GRAY_F,
    GRAY_E,
    fs=9.5,
)

# Administrator (bottom-left)
rbox(
    ax,
    0.85,
    1.9,
    2.2,
    0.82,
    ["Administrator", "manages projects & docs"],
    GRAY_F,
    GRAY_E,
    fs=9.5,
)

# ── Right external systems ────────────────────────────────────────────────────
# Anthropic LLM (top-right, dashed)
rbox(
    ax,
    11.2,
    3.6,
    2.3,
    0.82,
    ["LLM API", "(e.g. Claude / GPT)"],
    PINK_F,
    PINK_E,
    fs=9.5,
    linestyle="dashed",
)

# Embedding Provider (bottom-right, dashed)
rbox(
    ax,
    11.2,
    1.9,
    2.3,
    0.82,
    ["Embedding Provider", "BGE-M3 / Cohere / OpenAI"],
    PINK_F,
    PINK_E,
    fs=9.5,
    linestyle="dashed",
)

# ── Arrows ────────────────────────────────────────────────────────────────────
# User → platform  (grey right edge: 0.85+1.1=1.95)
arr(ax, 1.96, 3.60, 3.30, 3.60, "REST / SSE")
# Admin → platform
arr(ax, 1.96, 1.90, 3.30, 1.90, "REST")
# platform → Anthropic  (pink left edge: 11.2-1.15=10.05)
arr(ax, 8.70, 3.60, 10.04, 3.60, "HTTPS")
# platform → Embedding
arr(ax, 8.70, 1.90, 10.04, 1.90, "HTTPS")

plt.tight_layout(pad=0.3)
plt.savefig("c4_context.png", dpi=200, bbox_inches="tight")
print("Saved c4_context.png")
