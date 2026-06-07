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
ACT_E = "#5570aa"  # activation boxes

PARTICIPANTS = [
    "Client",
    "API Gateway",
    "Orchestrator",
    "Retrieval +\nReranker",
    "Generation",
]
N = len(PARTICIPANTS)
X = [1.2, 3.3, 5.4, 7.5, 9.6]  # x positions for lifelines

# ── canvas ────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(13, 8))
ax.set_xlim(0, 11.5)
ax.set_ylim(0, 8.5)
ax.axis("off")

# ── participant boxes (top) ───────────────────────────────────────────────────
BOX_W = 1.8
BOX_H = 0.60
for i, (x, name) in enumerate(zip(X, PARTICIPANTS)):
    p = FBP(
        (x - BOX_W / 2, 7.75),
        BOX_W,
        BOX_H,
        boxstyle="round,pad=0.05",
        linewidth=1.2,
        edgecolor=BLUE_E,
        facecolor=BLUE_F,
        zorder=2,
    )
    ax.add_patch(p)
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
Y_TOP = 7.75
Y_BOT = 0.3
for x in X:
    ax.plot([x, x], [Y_TOP, Y_BOT], color="#cccccc", lw=1.0, linestyle="--", zorder=0)


# ── activation boxes ─────────────────────────────────────────────────────────
def activation(ax, xi, y_top, y_bot, w=0.15):
    p = FBP(
        (X[xi] - w / 2, y_bot),
        w,
        y_top - y_bot,
        boxstyle="square,pad=0",
        linewidth=0.8,
        edgecolor=ACT_E,
        facecolor=ACT_F,
        zorder=2,
    )
    ax.add_patch(p)


# Orchestrator active: from row 1 response down to query.completed
activation(ax, 2, 6.90, 0.80)
# Retrieval active: short
activation(ax, 3, 5.75, 5.10)
# Generation active
activation(ax, 4, 4.35, 3.30)


# ── messages ─────────────────────────────────────────────────────────────────
def msg(ax, xi, xj, y, label, dash=False, dot=False, lw=1.1):
    x0, x1 = X[xi], X[xj]
    if dot:
        ls = ":"
    elif dash:
        ls = "--"
    else:
        ls = "-"
    color = DASHED if (dash or dot) else ARROW
    ax.annotate(
        "",
        xy=(x1, y),
        xytext=(x0, y),
        arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, linestyle=ls),
        zorder=3,
    )
    mx = (x0 + x1) / 2
    ax.text(
        mx, y + 0.10, label, ha="center", va="bottom", fontsize=8.5, color="#333333"
    )


# 1. Client → API Gateway: POST /chat/query
msg(ax, 0, 1, 7.20, "POST /chat/query")
# 2. API Gateway → Orchestrator: validate JWT + forward
msg(ax, 1, 2, 6.70, "validate JWT + forward")
# 3. Orchestrator → Retrieval: retrieve(q, k=20)
msg(ax, 2, 3, 5.90, "retrieve(q, k=20)")
# 4. Retrieval → Orchestrator: top-5 passages (dashed)
msg(ax, 3, 2, 5.10, "top-5 passages", dash=True)
# 5. Orchestrator → Generation: generate(q, passages)
msg(ax, 2, 4, 4.50, "generate(q, passages)")
# 6. Generation → Orchestrator: SSE stream (dashed)
msg(ax, 4, 2, 3.30, "SSE stream", dash=True)
# 7. Orchestrator → API Gateway: SSE stream (dashed)
msg(ax, 2, 1, 2.60, "SSE stream", dash=True)
# 8. API Gateway → Client: SSE stream proxied (dashed)
msg(ax, 1, 0, 1.90, "SSE stream (proxied)", dash=True)
# 9. Orchestrator → (right side note): query.completed async (dotted)
ax.annotate(
    "",
    xy=(X[4] + 0.2, 0.95),
    xytext=(X[2] + 0.08, 0.95),
    arrowprops=dict(arrowstyle="-|>", color=DASHED, lw=1.0, linestyle=":"),
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
