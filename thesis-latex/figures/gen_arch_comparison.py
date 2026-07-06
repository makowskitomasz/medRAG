"""Regenerate arch_comparison.png using matplotlib."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(9, 7))

# ── data ──────────────────────────────────────────────────────────────────────
# (name, x, y, size, color, bold_outline)
points = [
    ("Vanilla RAG", 0.12, 0.08, 900, "#8080cc", False),
    ("HyDE", 0.30, 0.11, 500, "#80b0e0", False),
    ("Self-RAG", 0.50, 0.43, 700, "#e0a060", False),
    ("Graph RAG", 0.27, 0.58, 700, "#e07090", False),
    ("Corr. RAG", 0.53, 0.28, 400, "#80cccc", False),
    ("Iter. Multi-hop", 0.64, 0.57, 650, "#60aaaa", False),
    ("MADAM-RAG", 0.68, 0.82, 700, "#e08080", False),
    ("rare-rag", 0.85, 0.70, 1400, "#60c060", True),
]

# Pareto frontier: Vanilla → Self-RAG → rare-rag
pareto_x = [0.12, 0.50, 0.85]
pareto_y = [0.08, 0.43, 0.70]
ax.plot(pareto_x, pareto_y, "g--", lw=1.8, zorder=1)
# place label right beside the line (at x=0.33, y_line≈0.27), just above it
ax.text(
    0.30,
    0.285,
    "Pareto frontier",
    ha="left",
    va="bottom",
    fontsize=9,
    color="#448844",
    style="italic",
    rotation=33,
)

# Per-label offsets: (dx, dy, ha)
# Dots ON the Pareto line get labels placed to side/below so they don't sit on the line.
# Dots off the line get labels toward the clear space.
LABEL_OFFSETS = {
    # (dx, dy, ha)  — offsets ≈ circle radius + 2pt margin in data coords
    "Vanilla RAG": (0.02, -0.052, "left"),  # below-right
    "HyDE": (0.00, 0.040, "center"),  # above
    "Self-RAG": (-0.034, 0.008, "right"),  # left (on Pareto line)
    "Graph RAG": (0.028, 0.036, "left"),  # above-right
    "Corr. RAG": (0.022, 0.010, "left"),  # right
    "Iter. Multi-hop": (0.028, -0.008, "left"),  # right (on Pareto line)
    "MADAM-RAG": (-0.028, 0.036, "right"),  # above-left
    "rare-rag": (0.00, 0.050, "center"),  # above
}

# Scatter
for name, x, y, sz, color, bold in points:
    lw = 2.5 if bold else 0.8
    ec = "#228822" if bold else "#888888"
    ax.scatter(x, y, s=sz, color=color, edgecolors=ec, linewidths=lw, zorder=3)
    dx, dy, ha = LABEL_OFFSETS.get(name, (0.04, 0.05, "left"))
    is_rare = name == "rare-rag"
    ax.text(
        x + dx,
        y + dy,
        name,
        ha=ha,
        va="bottom",
        fontsize=10 if is_rare else 9.5,
        fontweight="bold" if is_rare else "normal",
        color="#226622" if is_rare else "#333333",
        zorder=4,
    )

# ── axes styling ──────────────────────────────────────────────────────────────
ax.set_xlim(-0.05, 1.10)
ax.set_ylim(-0.05, 1.10)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.spines["left"].set_color("#888888")
ax.spines["bottom"].set_color("#888888")

# X axis
ax.set_xticks([0.15, 0.50, 0.85])
ax.set_xticklabels(
    ["fixed", "moderate", "fully adaptive"], fontsize=10, color="#888888"
)
ax.set_xlabel("Retrieval adaptivity", fontsize=12, fontweight="bold", labelpad=8)

# Y axis
ax.set_yticks([0.10, 0.50, 0.90])
ax.set_yticklabels(
    ["single-pass", "iterative", "multi-agent"],
    fontsize=10,
    color="#888888",
    rotation=90,
    va="center",
)
ax.set_ylabel("Generation complexity", fontsize=12, fontweight="bold", labelpad=8)

# Light grid lines matching the original
for xg in [0.15, 0.50, 0.85]:
    ax.axvline(xg, color="#dddddd", lw=0.8, zorder=0)
for yg in [0.10, 0.50, 0.90]:
    ax.axhline(yg, color="#dddddd", lw=0.8, zorder=0)

# Arrow heads on axes
ax.annotate(
    "",
    xy=(1.08, 0),
    xytext=(1.0, 0),
    arrowprops=dict(arrowstyle="-|>", color="#888888", lw=1.1),
)
ax.annotate(
    "",
    xy=(0, 1.08),
    xytext=(0, 1.0),
    arrowprops=dict(arrowstyle="-|>", color="#888888", lw=1.1),
)

plt.tight_layout(pad=0.5)
plt.savefig("arch_comparison.png", dpi=200, bbox_inches="tight")
print("Saved arch_comparison.png")
