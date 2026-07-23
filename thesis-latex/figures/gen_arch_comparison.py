"""Regenerate arch_comparison.png using matplotlib."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(9, 7))

# ── data ──────────────────────────────────────────────────────────────────────
# Qualitative positioning map: coordinates are conceptual, not measured.
# All markers are the same size (size carries no data); rare-rag is highlighted
# only by a bold green outline to mark it as this thesis's architecture.
# (name, x, y, color, bold_outline)
_SZ = 650
points = [
    ("Vanilla RAG", 0.12, 0.08, "#8080cc", False),
    ("HyDE", 0.30, 0.11, "#80b0e0", False),
    ("Self-RAG", 0.50, 0.43, "#e0a060", False),
    ("Graph RAG", 0.27, 0.58, "#e07090", False),
    ("Corr. RAG", 0.53, 0.28, "#80cccc", False),
    ("Iter. Multi-hop", 0.64, 0.57, "#60aaaa", False),
    ("MADAM-RAG", 0.68, 0.82, "#e08080", False),
    ("rare-rag", 0.85, 0.70, "#60c060", True),
]

# Per-label offsets: (dx, dy, ha)
LABEL_OFFSETS = {
    "Vanilla RAG": (0.02, -0.052, "left"),
    "HyDE": (0.00, 0.040, "center"),
    "Self-RAG": (-0.034, 0.008, "right"),
    "Graph RAG": (0.028, 0.036, "left"),
    "Corr. RAG": (0.022, 0.010, "left"),
    "Iter. Multi-hop": (0.028, -0.008, "left"),
    "MADAM-RAG": (-0.028, 0.036, "right"),
    "rare-rag": (0.00, 0.050, "center"),
}

# Scatter
for name, x, y, color, bold in points:
    lw = 2.5 if bold else 0.8
    ec = "#228822" if bold else "#888888"
    ax.scatter(x, y, s=_SZ, color=color, edgecolors=ec, linewidths=lw, zorder=3)
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
