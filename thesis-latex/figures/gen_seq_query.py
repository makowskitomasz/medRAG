"""Regenerate seq_query.png — UML sequence diagram using matplotlib."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch as FBP

BLUE_F = "#dce6f7"
BLUE_E = "#6b8ec7"
ARROW = "#222222"
DASHED = "#888888"
ACT_F = "#9aabcc"
ACT_E = "#5570aa"

PARTICIPANTS = [
    "Client",
    "API Gateway",
    "Orchestrator",
    "Retrieval +\nReranker",
    "Generation",
]
X = [1.2, 3.3, 5.4, 7.5, 9.2]
AW = 0.075  # activation box half-width

# ── canvas ────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(11, 8))
ax.set_xlim(0, 10.5)
ax.set_ylim(0, 8.5)
ax.axis("off")

# ── participant boxes (top) ───────────────────────────────────────────────────
BOX_W = 1.8
BOX_H = 0.60
for x, name in zip(X, PARTICIPANTS):
    ax.add_patch(
        FBP(
            (x - BOX_W / 2, 7.75),
            BOX_W,
            BOX_H,
            boxstyle="round,pad=0.05",
            linewidth=1.2,
            edgecolor=BLUE_E,
            facecolor=BLUE_F,
            zorder=2,
        )
    )
    ax.text(
        x,
        7.75 + BOX_H / 2,
        name,
        ha="center",
        va="center",
        fontsize=9.5,
        fontweight="bold",
        multialignment="center",
        zorder=3,
    )

# ── lifelines ─────────────────────────────────────────────────────────────────
for x in X:
    ax.plot([x, x], [7.75, 0.3], color="#cccccc", lw=1.0, linestyle="--", zorder=0)


# ── activation boxes ─────────────────────────────────────────────────────────
def activation(ax, xi, y_top, y_bot, w=0.15):
    ax.add_patch(
        FBP(
            (X[xi] - w / 2, y_bot),
            w,
            y_top - y_bot,
            boxstyle="square,pad=0",
            linewidth=0.8,
            edgecolor=ACT_E,
            facecolor=ACT_F,
            zorder=2,
        )
    )


# Tops aligned to y of triggering message, bots to y of last return
activation(ax, 2, 6.70, 0.80)  # Orchestrator: msg 2 arrival → query.completed
activation(ax, 3, 5.90, 5.10)  # Retrieval:    msg 3 arrival → msg 4 return
activation(ax, 4, 4.50, 3.30)  # Generation:   msg 5 arrival → msg 6 return


# ── messages ─────────────────────────────────────────────────────────────────
def msg(ax, x0, y, x1, label, dash=False, dot=False, lw=1.1):
    """Arrow from (x0,y) to (x1,y) with label above midpoint."""
    ls = ":" if dot else ("--" if dash else "-")
    color = DASHED if (dash or dot) else ARROW
    ax.annotate(
        "",
        xy=(x1, y),
        xytext=(x0, y),
        arrowprops=dict(
            arrowstyle="-|>", color=color, lw=lw, linestyle=ls, shrinkA=0, shrinkB=0
        ),
        zorder=3,
    )
    ax.text(
        (x0 + x1) / 2,
        y + 0.10,
        label,
        ha="center",
        va="bottom",
        fontsize=8.5,
        color="#333333",
    )


# 1. Client → API Gateway  (no activation boxes → lifeline centres)
msg(ax, X[0], 7.20, X[1], "POST /chat/query")

# 2. API Gateway → Orchestrator  (Orchestrator activation starts here)
#    tip lands on Orchestrator activation left edge
msg(ax, X[1], 6.70, X[2] - AW, "validate JWT + forward")

# 3. Orchestrator → Retrieval  (both active → right/left edges)
msg(ax, X[2] + AW, 5.90, X[3] - AW, "retrieve(q, k=20)")

# 4. Retrieval → Orchestrator  (return left → left/right edges)
msg(ax, X[3] - AW, 5.10, X[2] + AW, "top-5 passages", dash=True)

# 5. Orchestrator → Generation  (Generation activation starts here)
msg(ax, X[2] + AW, 4.50, X[4] - AW, "generate(q, passages)")

# 6. Generation → Orchestrator  (return left → left/right edges)
msg(ax, X[4] - AW, 3.30, X[2] + AW, "SSE stream", dash=True)

# 7. Orchestrator → API Gateway  (going left → Orchestrator left edge)
msg(ax, X[2] - AW, 2.60, X[1], "SSE stream", dash=True)

# 8. API Gateway → Client  (no activation boxes)
msg(ax, X[1], 1.90, X[0], "SSE stream (proxied)", dash=True)

# 9. query.completed async (dotted) — from Orchestrator right edge to Generation
ax.annotate(
    "",
    xy=(X[4], 0.95),
    xytext=(X[2] + AW, 0.95),
    arrowprops=dict(
        arrowstyle="-|>", color=DASHED, lw=1.0, linestyle=":", shrinkA=0, shrinkB=0
    ),
    zorder=3,
)
ax.text(
    (X[2] + X[4]) / 2,
    1.05,
    "query.completed (async)",
    ha="center",
    va="bottom",
    fontsize=8.5,
    color="#888888",
)

plt.tight_layout(pad=0.2)
plt.savefig("seq_query.png", dpi=200, bbox_inches="tight")
print("Saved seq_query.png")
