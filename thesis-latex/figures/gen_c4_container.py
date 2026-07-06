"""Generate C4 container diagram (level 2) for medRAG."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch as FBP
import matplotlib.patches as mpatches

# Colors
BLUE_F = "#dce6f7"
BLUE_E = "#6b8ec7"
ORAN_F = "#fde8cc"
ORAN_E = "#d08040"
GREEN_F = "#d5f0dc"
GREEN_E = "#5aaa6a"
GRAY_F = "#ebebeb"
GRAY_E = "#aaaaaa"
PURPLE_F = "#e8dff5"
PURPLE_E = "#8b6bbd"
ARROW = "#555555"

# Smaller boxes
BW, BH = 1.3, 0.55  # box width, height
CW, CH = 1.2, 0.5  # cylinder width, height
HEAD_LEN = 0.04
HEAD_W = 0.025


def rbox(ax, cx, cy, w, h, lines, face, edge, fs=7):
    from matplotlib.patches import Rectangle

    p = Rectangle(
        (cx - w / 2, cy - h / 2),
        w,
        h,
        linewidth=0.8,
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
        fontfamily="DejaVu Sans",
        zorder=3,
    )


def cylinder(ax, cx, cy, w, h, lines, fs=7):
    eh = 0.12
    body = FBP(
        (cx - w / 2, cy - h / 2),
        w,
        h,
        boxstyle="square,pad=0",
        linewidth=0.8,
        edgecolor=GRAY_E,
        facecolor=GRAY_F,
        zorder=2,
    )
    ax.add_patch(body)
    top = mpatches.Ellipse(
        (cx, cy + h / 2),
        w,
        eh,
        linewidth=0.8,
        edgecolor=GRAY_E,
        facecolor=GRAY_F,
        zorder=3,
    )
    ax.add_patch(top)
    bot = mpatches.Arc(
        (cx, cy - h / 2),
        w,
        eh,
        theta1=180,
        theta2=360,
        linewidth=0.8,
        edgecolor=GRAY_E,
        zorder=3,
    )
    ax.add_patch(bot)
    ax.text(
        cx,
        cy,
        "\n".join(lines),
        ha="center",
        va="center",
        fontsize=fs,
        multialignment="center",
        zorder=4,
    )


def section_label(ax, x, y, text):
    ax.text(
        x,
        y,
        text,
        ha="left",
        va="center",
        fontsize=8,
        fontweight="bold",
        color="#444444",
        zorder=5,
    )


def arr(ax, x0, y0, x1, y1, dashed=False):
    dx, dy = x1 - x0, y1 - y0
    length = (dx**2 + dy**2) ** 0.5
    if length < 1e-6:
        return
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    bx = x1 - ux * HEAD_LEN
    by = y1 - uy * HEAD_LEN
    style = "--" if dashed else "-"
    ax.plot(
        [x0, bx],
        [y0, by],
        color=ARROW,
        lw=0.8,
        ls=style,
        zorder=4,
        solid_capstyle="butt",
    )
    tri = plt.Polygon(
        [
            (x1, y1),
            (bx + px * HEAD_W, by + py * HEAD_W),
            (bx - px * HEAD_W, by - py * HEAD_W),
        ],
        closed=True,
        facecolor=ARROW,
        edgecolor=ARROW,
        zorder=4,
    )
    ax.add_patch(tri)


fig, ax = plt.subplots(figsize=(12, 8))
ax.set_xlim(0, 12)
ax.set_ylim(0, 8)
ax.axis("off")

# Spacing - exact half dimensions for arrow endpoints
hw, hh = BW / 2, BH / 2
chw, chh = CW / 2, CH / 2

# Row Y positions
ROW1 = 7.0  # top row (gateway, orchestrator, query-processor, admin)
ROW2 = 5.8  # second row (auth, retrieval, reranker, generation, eval)
ROW3 = 4.0  # ingestion pipeline
ROW4 = 2.6  # data stores
ROW5 = 1.2  # RabbitMQ

# Column X positions (centered layout)
C_GW = 1.0  # gateway/auth
C_ORCH = 3.0  # orchestrator
C_QP = 4.5  # query-processor
C_RET = 3.0  # retrieval
C_RER = 4.5  # reranker
C_GEN = 6.0  # generation
C_ADM = 8.0  # admin/eval
C_ING = 1.0  # ingestion
C_PAR = 2.5  # parser
C_CHU = 4.0  # chunking
C_EMB = 5.5  # embedding
C_IDX = 7.0  # indexing
C_DB = 10.0  # MongoDB/Weaviate
C_MQ = 4.0  # RabbitMQ

# === SECTION LABELS ===
section_label(ax, 0.3, 7.6, "Gateway & Auth")
section_label(ax, 2.5, 7.6, "Query Pipeline (sync)")
section_label(ax, 0.3, 4.6, "Ingestion Pipeline (async)")
section_label(ax, 7.5, 7.6, "Admin & Eval")
section_label(ax, 9.0, 3.5, "Data Stores")

# === BOXES ===
# Gateway & Auth
rbox(ax, C_GW, ROW1, BW, BH, ["api-gateway", "(8000)"], BLUE_F, BLUE_E)
rbox(ax, C_GW, ROW2, BW, BH, ["auth", "(8001)"], BLUE_F, BLUE_E)

# Query Pipeline
rbox(ax, C_ORCH, ROW1, BW, BH, ["orchestrator", "(8002)"], BLUE_F, BLUE_E)
rbox(ax, C_QP, ROW1, BW, BH, ["query-proc", "(8003)"], BLUE_F, BLUE_E)
rbox(ax, C_RET, ROW2, BW, BH, ["retrieval", "(8004)"], BLUE_F, BLUE_E)
rbox(ax, C_RER, ROW2, BW, BH, ["reranker", "(8005)"], BLUE_F, BLUE_E)
rbox(ax, C_GEN, ROW2, BW, BH, ["generation", "(8006)"], BLUE_F, BLUE_E)

# Ingestion Pipeline
rbox(ax, C_ING, ROW3, BW, BH, ["ingestion", "(8007)"], ORAN_F, ORAN_E)
rbox(ax, C_PAR, ROW3, BW, BH, ["parser", "(8008)"], ORAN_F, ORAN_E)
rbox(ax, C_CHU, ROW3, BW, BH, ["chunking", "(8009)"], ORAN_F, ORAN_E)
rbox(ax, C_EMB, ROW3, BW, BH, ["embedding", "(8010)"], ORAN_F, ORAN_E)
rbox(ax, C_IDX, ROW3, BW, BH, ["indexing", "(8011)"], ORAN_F, ORAN_E)

# Admin & Eval
rbox(ax, C_ADM, ROW1, BW, BH, ["admin", "(8012)"], GREEN_F, GREEN_E)
rbox(ax, C_ADM, ROW2, BW, BH, ["eval", "(8013)"], GREEN_F, GREEN_E)

# Data Stores
cylinder(ax, C_DB, ROW4 + 0.4, CW, CH, ["MongoDB"])
cylinder(ax, C_DB, ROW4 - 0.4, CW, CH, ["Weaviate"])

# RabbitMQ
rbox(ax, C_MQ, ROW5, 1.5, BH, ["RabbitMQ"], PURPLE_F, PURPLE_E)


# === ARROWS ===
# Helper for L-shaped arrows (orthogonal routing)
def L_arr(ax, x0, y0, x1, y1, corner, dashed=False):
    """Draw L-shaped arrow: start->corner->end"""
    cx, cy = corner
    style = "--" if dashed else "-"
    ax.plot([x0, cx], [y0, cy], color=ARROW, lw=0.8, ls=style, zorder=4)
    arr(ax, cx, cy, x1, y1, dashed=dashed)


# Gateway & Auth
arr(ax, C_GW, ROW1 - hh, C_GW, ROW2 + hh)  # gateway -> auth
arr(ax, C_GW + hw, ROW1, C_ORCH - hw, ROW1)  # gateway -> orchestrator

# Query Pipeline
arr(ax, C_ORCH + hw, ROW1, C_QP - hw, ROW1)  # orchestrator -> query-processor
arr(ax, C_ORCH, ROW1 - hh, C_RET, ROW2 + hh)  # orchestrator -> retrieval
arr(ax, C_RET + hw, ROW2, C_RER - hw, ROW2)  # retrieval -> reranker
arr(ax, C_RER + hw, ROW2, C_GEN - hw, ROW2)  # reranker -> generation

# Ingestion Pipeline (dashed)
arr(ax, C_ING + hw, ROW3, C_PAR - hw, ROW3, dashed=True)
arr(ax, C_PAR + hw, ROW3, C_CHU - hw, ROW3, dashed=True)
arr(ax, C_CHU + hw, ROW3, C_EMB - hw, ROW3, dashed=True)
arr(ax, C_EMB + hw, ROW3, C_IDX - hw, ROW3, dashed=True)

# Ingestion -> RabbitMQ (L-shape: down then right)
MQ_HW = 0.75  # RabbitMQ half-width
L_arr(ax, C_ING, ROW3 - hh, C_MQ - MQ_HW, ROW5, (C_ING, ROW5), dashed=True)

# Retrieval -> Weaviate (down from retrieval, right above ingestion, down after indexing, then to Weaviate)
ABOVE_ING_Y = ROW3 + hh + 0.15  # above ingestion pipeline
AFTER_IDX_X = C_IDX + hw + 0.15  # after indexing
ax.plot(
    [C_RET, C_RET], [ROW2 - hh, ABOVE_ING_Y], color=ARROW, lw=0.8, zorder=1
)  # down from retrieval
ax.plot(
    [C_RET, AFTER_IDX_X], [ABOVE_ING_Y, ABOVE_ING_Y], color=ARROW, lw=0.8, zorder=1
)  # right above ingestion
ax.plot(
    [AFTER_IDX_X, AFTER_IDX_X], [ABOVE_ING_Y, ROW4 - 0.4], color=ARROW, lw=0.8, zorder=1
)  # down after indexing
arr(ax, AFTER_IDX_X, ROW4 - 0.4, C_DB - chw, ROW4 - 0.4)  # right to Weaviate

# Indexing -> Weaviate (down then right)
WEAV_Y = ROW4 - 0.4
MONGO_Y = ROW4 + 0.4
IDX_WEAV_Y = WEAV_Y - 0.15  # at Weaviate level but lower than retrieval line
ax.plot(
    [C_IDX + 0.2, C_IDX + 0.2], [ROW3 - hh, IDX_WEAV_Y], color=ARROW, lw=0.8, zorder=1
)  # down from indexing
arr(ax, C_IDX + 0.2, IDX_WEAV_Y, C_DB - chw, IDX_WEAV_Y)  # right to Weaviate left edge

# Indexing -> MongoDB (down then right)
ax.plot(
    [C_IDX, C_IDX], [ROW3 - hh, MONGO_Y], color=ARROW, lw=0.8, zorder=1
)  # down from indexing
arr(ax, C_IDX, MONGO_Y, C_DB - chw, MONGO_Y)  # right to MongoDB

# Eval -> RabbitMQ (route right of indexing, then down, then left)
EVAL_RIGHT_X = (
    C_IDX + hw + 0.3
)  # right of indexing (offset from retrieval->weaviate line)
ax.plot(
    [C_ADM - hw, EVAL_RIGHT_X], [ROW2, ROW2], color=ARROW, lw=0.8, ls="--", zorder=1
)  # left from eval
ax.plot(
    [EVAL_RIGHT_X, EVAL_RIGHT_X], [ROW2, ROW5], color=ARROW, lw=0.8, ls="--", zorder=1
)  # down
arr(ax, EVAL_RIGHT_X, ROW5, C_MQ + MQ_HW, ROW5, dashed=True)  # left to RabbitMQ

# Admin -> MongoDB (right then down to MongoDB top)
ax.plot(
    [C_ADM + hw, C_DB], [ROW1, ROW1], color=ARROW, lw=0.8, zorder=1
)  # right from admin
arr(ax, C_DB, ROW1, C_DB, MONGO_Y + chh + 0.08)  # down to MongoDB top

# Eval -> MongoDB (right then down)
ax.plot(
    [C_ADM + hw, C_DB + 0.15], [ROW2, ROW2], color=ARROW, lw=0.8, zorder=1
)  # right from eval
arr(ax, C_DB + 0.15, ROW2, C_DB + 0.15, MONGO_Y + chh + 0.08)  # down to MongoDB top

plt.savefig("c4_container.png", dpi=200, bbox_inches="tight")
print("Saved c4_container.png")
