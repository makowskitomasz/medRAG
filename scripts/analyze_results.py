#!/usr/bin/env python3
"""
Analyze benchmark results and generate summary tables + plots.

Reads:
  - One or more result JSON files from benchmark_runner.py
  - MongoDB eval_results collection (faithfulness, answer_relevance, rouge_l, etc.)

Writes:
  results/summary_table.csv
  results/plots/token_f1_em.png
  results/plots/faithfulness_by_mode.png
  results/plots/latency_by_mode.png
  results/plots/latency_vs_quality.png
  results/plots/heatmap.png
  results/plots/radar.png

Usage:
    python scripts/analyze_results.py \\
        --input results/hotpotqa_results.json \\
        --mongo-uri mongodb://localhost:27017 \\
        --project-id <PROJECT_ID> \\
        --output-dir results/
"""

import argparse
import json
from pathlib import Path
from typing import Any

RAG_MODES = [
    "vanilla",
    "hyde",
    "query_rewriting",
    "self_reflection",
    "multi_agent",
    "corrective_rag",
    "iterative_multihop",
    "madam_rag",
    "rare_rag",
]

METRIC_COLS = [
    "token_f1",
    "em",
    "rouge_l",
    "faithfulness",
    "answer_correctness",
    "answer_relevance",
    "context_recall",
    "token_count",
    "latency_ms",
]

RAG_MODE_LABELS = {
    "vanilla": "Vanilla",
    "hyde": "HyDE",
    "query_rewriting": "Query Rewriting",
    "self_reflection": "Self-Reflection",
    "multi_agent": "Multi-Agent",
    "corrective_rag": "Corrective RAG",
    "iterative_multihop": "Iterative Multihop",
    "madam_rag": "MADAM RAG",
    "rare_rag": "RARE RAG",
}


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Analyze medRAG benchmark results")
    p.add_argument("--input", nargs="+", required=True)
    p.add_argument("--mongo-uri", default="mongodb://localhost:27017")
    p.add_argument("--project-id", default=None)
    p.add_argument("--output-dir", default="results")
    return p.parse_args()


def _load_latency(paths: list[str]) -> Any:
    """Load latency + token_count from JSON files, deduplicated."""
    import pandas as pd

    rows: list[dict] = []
    for path in paths:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        rows.extend(data)
    df = pd.DataFrame(rows)
    if "error" in df.columns:
        df = df[df["error"].isna()]
    keep = [c for c in ["question", "rag_mode", "latency_ms", "token_count"] if c in df.columns]
    df = df[keep].drop_duplicates(subset=["question", "rag_mode"], keep="last")
    return df.reset_index(drop=True)


def _load_results(paths: list[str]) -> Any:
    """Kept for backward compat — actual data comes from MongoDB."""
    return _load_latency(paths)


def _enrich_from_mongo(df: Any, mongo_uri: str, project_id: str | None) -> Any:
    import pandas as pd
    from pymongo import MongoClient

    try:
        client: MongoClient = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
        client.admin.command("ping")
    except Exception as exc:
        print(f"[WARN] Cannot connect to MongoDB ({exc}) — skipping metric enrichment")
        return df

    db = client["medrag"]
    query: dict = {}
    if project_id:
        query["project_id"] = project_id

    eval_rows = list(db["eval_results"].find(query, {"_id": 0}))
    if not eval_rows:
        print("[WARN] No eval_results found in MongoDB")
        return df

    eval_df = pd.DataFrame(eval_rows)
    metrics_df = pd.json_normalize(eval_df["metrics"])
    eval_df = pd.concat([eval_df.drop(columns=["metrics"]), metrics_df], axis=1)

    # Deduplicate: per (question, rag_mode) keep latest by timestamp
    if "timestamp" in eval_df.columns:
        eval_df["timestamp"] = pd.to_datetime(eval_df["timestamp"], utc=True)
        eval_df = eval_df.sort_values("timestamp").drop_duplicates(
            subset=["question", "rag_mode"], keep="last"
        )
    else:
        eval_df = eval_df.drop_duplicates(subset=["question", "rag_mode"], keep="last")

    metric_cols = [
        c for c in METRIC_COLS if c in eval_df.columns and c not in ("token_count", "latency_ms")
    ]
    # latency_ms and token_count from MongoDB metrics (complete coverage)
    for extra in ("latency_ms", "token_count"):
        metric_cols_all = metric_cols + [extra] if extra in eval_df.columns else metric_cols
    metric_cols_all = metric_cols + [
        c for c in ("latency_ms", "token_count") if c in eval_df.columns
    ]
    print(f"  Eval rows (deduped): {len(eval_df)}  metrics: {metric_cols}")

    # Build main DataFrame from MongoDB — join latency from JSON
    base_cols = ["question", "rag_mode"] + metric_cols_all
    result_df = eval_df[[c for c in base_cols if c in eval_df.columns]].copy()

    client.close()
    return result_df


def _compute_summary(df: Any) -> Any:
    import numpy as np

    quality_cols = [
        c
        for c in [
            "token_f1",
            "em",
            "rouge_l",
            "faithfulness",
            "answer_correctness",
            "answer_relevance",
            "context_recall",
        ]
        if c in df.columns
    ]
    # Quality metrics: mean only
    agg: dict = {col: "mean" for col in quality_cols}

    summary = df.groupby("rag_mode").agg(agg)
    summary.columns = [
        col if isinstance(col, str) else "_".join(str(c) for c in col).strip("_")
        for col in summary.columns
    ]

    # Latency separately to avoid MultiIndex pollution
    if "latency_ms" in df.columns:
        lat = df.groupby("rag_mode")["latency_ms"].agg(
            latency_ms_mean="mean",
            latency_ms_median="median",
            latency_ms_p95=lambda x: np.percentile(x.dropna(), 95),
        )
        summary = summary.join(lat)
    if "token_count" in df.columns:
        summary["token_count"] = df.groupby("rag_mode")["token_count"].mean()

    summary["n"] = df.groupby("rag_mode").size()

    # Reorder rows to match RAG_MODES order
    order = [m for m in RAG_MODES if m in summary.index]
    summary = summary.loc[order]

    return summary.reset_index()


def _plot_token_f1_em(df: Any, plots_dir: Path) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    cols = [c for c in ["token_f1", "em", "rouge_l"] if c in df.columns]
    if not cols:
        print("  [SKIP] token_f1_em.png — no token_f1/em/rouge_l data")
        return

    order = [m for m in RAG_MODES if m in df["rag_mode"].unique()]
    labels = [RAG_MODE_LABELS.get(m, m) for m in order]
    x = np.arange(len(order))
    width = 0.25
    colors = ["#2196F3", "#4CAF50", "#FF9800"]

    fig, ax = plt.subplots(figsize=(12, 5))
    for i, col in enumerate(cols):
        means = [df[df["rag_mode"] == m][col].mean() for m in order]
        ax.bar(
            x + i * width,
            means,
            width,
            label=col.replace("_", " ").upper(),
            color=colors[i],
            alpha=0.85,
        )

    ax.set_xticks(x + width)
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_ylabel("Score")
    ax.set_title("Token F1 / EM / ROUGE-L by RAG Mode", fontsize=13)
    ax.set_ylim(0, 1)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    out = plots_dir / "token_f1_em.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out}")


def _plot_faithfulness(df: Any, plots_dir: Path) -> None:
    import matplotlib.pyplot as plt
    import seaborn as sns

    if "faithfulness" not in df.columns or df["faithfulness"].isna().all():
        print("  [SKIP] faithfulness_by_mode.png — no faithfulness data")
        return

    order = [m for m in RAG_MODES if m in df["rag_mode"].unique()]
    labels = [RAG_MODE_LABELS.get(m, m) for m in order]

    fig, ax = plt.subplots(figsize=(11, 5))
    sns.barplot(
        data=df.dropna(subset=["faithfulness"]),
        x="rag_mode",
        y="faithfulness",
        hue="rag_mode",
        order=order,
        ax=ax,
        palette="Blues_d",
        errorbar="ci",
        legend=False,
    )
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_title("Faithfulness by RAG Mode", fontsize=13)
    ax.set_xlabel("")
    ax.set_ylabel("Faithfulness (LLM-as-judge)")
    ax.set_ylim(0, 1)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    out = plots_dir / "faithfulness_by_mode.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out}")


def _plot_latency(df: Any, plots_dir: Path) -> None:
    import matplotlib.pyplot as plt
    import seaborn as sns

    if "latency_ms" not in df.columns or df["latency_ms"].isna().all():
        print("  [SKIP] latency_by_mode.png — no latency data")
        return

    order = [m for m in RAG_MODES if m in df["rag_mode"].unique()]
    labels = [RAG_MODE_LABELS.get(m, m) for m in order]

    fig, ax = plt.subplots(figsize=(11, 5))
    sns.boxplot(
        data=df.dropna(subset=["latency_ms"]),
        x="rag_mode",
        y="latency_ms",
        hue="rag_mode",
        order=order,
        ax=ax,
        palette="Oranges",
        legend=False,
    )
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_title("Latency by RAG Mode (ms)", fontsize=13)
    ax.set_xlabel("")
    ax.set_ylabel("Latency (ms)")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    out = plots_dir / "latency_by_mode.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out}")


def _plot_latency_vs_quality(summary: Any, plots_dir: Path) -> None:
    import matplotlib.pyplot as plt

    x_col = "latency_ms_median"
    y_col = "token_f1" if "token_f1" in summary.columns else "faithfulness_mean"
    if y_col == "token_f1" and "token_f1" not in summary.columns:
        print("  [SKIP] latency_vs_quality.png — missing data")
        return
    if x_col not in summary.columns:
        print("  [SKIP] latency_vs_quality.png — missing latency data")
        return

    sub = summary.dropna(subset=[x_col, y_col])
    if sub.empty:
        return

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.scatter(sub[x_col] / 1000, sub[y_col], s=140, color="#2196F3", zorder=5)

    for _, row in sub.iterrows():
        ax.annotate(
            RAG_MODE_LABELS.get(row["rag_mode"], row["rag_mode"]),
            (row[x_col] / 1000, row[y_col]),
            textcoords="offset points",
            xytext=(8, 4),
            fontsize=9,
        )

    ax.set_title("Latency vs Token F1 per RAG Mode", fontsize=13)
    ax.set_xlabel("Median Latency (s)")
    ax.set_ylabel("Mean Token F1")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    out = plots_dir / "latency_vs_quality.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out}")


def _plot_heatmap(summary: Any, plots_dir: Path) -> None:
    import matplotlib.pyplot as plt
    import seaborn as sns

    metric_cols = [
        c
        for c in [
            "token_f1",
            "em",
            "rouge_l",
            "faithfulness",
            "answer_correctness",
            "answer_relevance",
            "context_recall",
        ]
        if c in summary.columns
    ]
    if not metric_cols:
        print("  [SKIP] heatmap.png — no quality metrics")
        return

    sub = summary.set_index("rag_mode")[metric_cols].copy()
    sub.index = [RAG_MODE_LABELS.get(m, m) for m in sub.index]
    sub.columns = [c.replace("_", " ").title() for c in sub.columns]

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.heatmap(
        sub.astype(float),
        annot=True,
        fmt=".3f",
        cmap="YlGnBu",
        vmin=0,
        vmax=1,
        ax=ax,
        linewidths=0.5,
        cbar_kws={"shrink": 0.8},
    )
    ax.set_title("Quality Metrics Heatmap — RAG Mode Comparison", fontsize=13)
    ax.set_xlabel("")
    ax.set_ylabel("")
    fig.tight_layout()
    out = plots_dir / "heatmap.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  {out}")


def _plot_radar(summary: Any, plots_dir: Path) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    metric_cols = [
        c
        for c in [
            "token_f1",
            "em",
            "rouge_l",
            "faithfulness",
            "answer_correctness",
            "answer_relevance",
            "context_recall",
        ]
        if c in summary.columns
    ]
    if len(metric_cols) < 3:
        print("  [SKIP] radar.png — need at least 3 metrics")
        return

    modes = [m for m in RAG_MODES if m in summary["rag_mode"].values]
    labels = [c.replace("_", " ").upper() for c in metric_cols]
    N = len(metric_cols)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    angles += angles[:1]

    colors = plt.cm.tab10.colors  # type: ignore[attr-defined]

    fig, ax = plt.subplots(figsize=(9, 9), subplot_kw={"polar": True})

    for i, mode in enumerate(modes):
        row = summary[summary["rag_mode"] == mode]
        if row.empty:
            continue
        values = [
            float(row[c].values[0]) if not row[c].isna().values[0] else 0.0 for c in metric_cols
        ]
        values += values[:1]
        ax.plot(
            angles,
            values,
            "o-",
            linewidth=1.8,
            color=colors[i % len(colors)],
            label=RAG_MODE_LABELS.get(mode, mode),
        )
        ax.fill(angles, values, alpha=0.08, color=colors[i % len(colors)])

    ax.set_thetagrids(np.degrees(angles[:-1]), labels, fontsize=10)
    ax.set_ylim(0, 1)
    ax.set_title("RAG Mode Comparison — All Metrics", fontsize=13, pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.15), fontsize=9)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out = plots_dir / "radar.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  {out}")


def _print_summary_table(summary: Any) -> None:
    quality_cols = [
        c
        for c in [
            "token_f1",
            "em",
            "rouge_l",
            "faithfulness",
            "answer_correctness",
            "answer_relevance",
            "context_recall",
        ]
        if c in summary.columns
    ]
    lat_col = "latency_ms_median" if "latency_ms_median" in summary.columns else None
    tok_col = "token_count" if "token_count" in summary.columns else None

    header_cols = (
        quality_cols + ([lat_col] if lat_col else []) + ([tok_col] if tok_col else []) + ["n"]
    )
    header = f"{'mode':<22}" + "".join(f"{c:>16}" for c in header_cols)
    print("\n" + "=" * len(header))
    print(header)
    print("=" * len(header))

    for _, row in summary.iterrows():
        line = f"{row['rag_mode']:<22}"
        for c in quality_cols:
            val = row.get(c)
            line += f"{val:>16.4f}" if val == val else f"{'—':>16}"
        if lat_col:
            val = row.get(lat_col)
            line += f"{val / 1000:>14.1f}s" if val == val else f"{'—':>16}"
        if tok_col:
            val = row.get(tok_col)
            line += f"{int(val):>16}" if val == val else f"{'—':>16}"
        line += f"{int(row['n']):>8}"
        print(line)
    print("=" * len(header))


def _print_rankings(summary: Any) -> None:
    rank_cols = {
        "Token F1": "token_f1",
        "EM": "em",
        "ROUGE-L": "rouge_l",
        "Faithfulness": "faithfulness",
        "Latency (lower=better)": "latency_ms_median",
    }
    print("\n── Rankings ─────────────────────────────────────")
    for label, col in rank_cols.items():
        if col not in summary.columns:
            continue
        ascending = "latency" in label.lower()
        ranked = summary.dropna(subset=[col]).sort_values(col, ascending=ascending)
        print(f"\n  {label}:")
        for i, (_, r) in enumerate(ranked[["rag_mode", col]].head(3).iterrows(), 1):
            val = r[col] / 1000 if "latency" in label.lower() else r[col]
            unit = "s" if "latency" in label.lower() else ""
            print(
                f"    {i}. {RAG_MODE_LABELS.get(r['rag_mode'], r['rag_mode']):<25} {val:.4f}{unit}"
            )


def main() -> None:
    args = _parse_args()

    try:
        import matplotlib
        import pandas  # noqa: F401
        import seaborn  # noqa: F401
    except ImportError as exc:
        raise SystemExit(f"Missing dependency: {exc}. Run: uv sync") from exc

    matplotlib.use("Agg")

    output_dir = Path(args.output_dir)
    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    print("Loading result files…")
    df = _load_results(args.input)
    print(f"  Rows loaded (deduped): {len(df)}")

    if df.empty:
        raise SystemExit("No valid results found.")

    print("Enriching with MongoDB eval metrics…")
    df = _enrich_from_mongo(df, args.mongo_uri, args.project_id)

    summary = _compute_summary(df)

    csv_path = output_dir / "summary_table.csv"
    summary.to_csv(csv_path, index=False)
    print(f"\nSummary table → {csv_path}")

    _print_summary_table(summary)

    print("\nGenerating plots…")
    _plot_token_f1_em(df, plots_dir)
    _plot_faithfulness(df, plots_dir)
    _plot_latency(df, plots_dir)
    _plot_latency_vs_quality(summary, plots_dir)
    _plot_heatmap(summary, plots_dir)
    _plot_radar(summary, plots_dir)

    _print_rankings(summary)
    print("\nDone.")


if __name__ == "__main__":
    main()
