#!/usr/bin/env python3
"""
Analyze DDI benchmark results with per-difficulty breakdown.

This extends the standard analyze_results.py with DDI-specific analysis:
  - Metrics per RAG mode (same as HotpotQA)
  - Metrics per difficulty level (1-5) for each mode
  - Delta table: agentic modes vs vanilla per difficulty
  - Plots: heatmap, bar chart per difficulty, radar chart

Reads:
  results/ddi_results.json   (output of benchmark_runner.py)
  MongoDB eval_results       (RAGAS metrics written by eval service)

Writes:
  results/ddi_summary.csv
  results/ddi_by_difficulty.csv
  results/plots/ddi_heatmap.png
  results/plots/ddi_difficulty_bar.png
  results/plots/ddi_agentic_vs_vanilla.png
  results/plots/ddi_radar.png

Usage:
    python scripts/analyze_ddi.py \\
        --input results/ddi_results.json \\
        --project-id <PROJECT_ID> \\
        [--mongo-uri mongodb://localhost:27017] \\
        [--output-dir results/]
"""

import argparse
import json
from collections import defaultdict
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

DIFFICULTY_LABELS = {
    1: "Easy",
    2: "Medium",
    3: "Hard",
    4: "Very Hard",
    5: "Expert",
}

AGENTIC_MODES = {"multi_agent", "iterative_multihop", "madam_rag", "rare_rag"}

METRIC_COLS = [
    "token_f1",
    "em",
    "rouge_l",
    "faithfulness",
    "answer_correctness",
    "answer_relevance",
    "context_recall",
    "latency_ms",
]

PRIMARY_METRIC = "faithfulness"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Analyze DDI benchmark results")
    p.add_argument("--input", required=True, help="Path to ddi_results.json")
    p.add_argument("--mongo-uri", default="mongodb://localhost:27017")
    p.add_argument("--project-id", default=None)
    p.add_argument("--output-dir", default="results")
    return p.parse_args()


def _load_results(path: str) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [r for r in data if "error" not in r and r.get("answer")]


def _enrich_from_mongo(results: list[dict], mongo_uri: str, project_id: str | None) -> list[dict]:
    try:
        from pymongo import MongoClient  # type: ignore[import]
    except ImportError:
        print("[WARN] pymongo not installed — skipping MongoDB enrichment")
        return results

    try:
        client: MongoClient = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
        client.admin.command("ping")
    except Exception as exc:
        print(f"[WARN] Cannot connect to MongoDB ({exc}) — using pre-enriched data only")
        return results

    db = client["medrag"]
    query: dict = {}
    if project_id:
        query["project_id"] = project_id

    eval_docs = list(
        db["eval_results"].find(
            query,
            {"_id": 1, "question": 1, "rag_mode": 1, "metrics": 1},
        )
    )
    client.close()

    lookup: dict[tuple[str, str], dict] = {
        (d["question"].strip(), d["rag_mode"]): d for d in eval_docs
    }
    enriched = 0
    for r in results:
        key = (r.get("question", "").strip(), r.get("rag_mode", ""))
        match = lookup.get(key)
        if match:
            for metric, val in match.get("metrics", {}).items():
                if r.get(metric) is None:
                    r[metric] = val
            enriched += 1

    print(f"Enriched {enriched}/{len(results)} results with RAGAS metrics from MongoDB")
    return results


def _avg(values: list[float]) -> float | None:
    clean = [v for v in values if v is not None]
    return sum(clean) / len(clean) if clean else None


def _get_difficulty(result: dict) -> int | None:
    meta = result.get("metadata", {})
    if isinstance(meta, dict):
        d = meta.get("difficulty") or meta.get("metadata", {}).get("difficulty")
        if d is not None:
            return int(d)
    level = result.get("level", "")
    mapping = {"easy": 1, "medium": 2, "hard": 3, "very hard": 4, "expert": 5}
    return mapping.get(level.lower())


def _build_summary(results: list[dict]) -> dict[str, dict[str, Any]]:
    by_mode: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        by_mode[r.get("rag_mode", "unknown")].append(r)

    summary: dict[str, dict[str, Any]] = {}
    for mode, rows in by_mode.items():
        summary[mode] = {
            "n": len(rows),
        }
        for m in METRIC_COLS:
            summary[mode][m] = _avg([r.get(m) for r in rows])
    return summary


def _build_difficulty_table(
    results: list[dict],
) -> dict[str, dict[int, dict[str, Any]]]:
    # {mode: {difficulty: {metric: avg}}}
    nested: dict[str, dict[int, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for r in results:
        mode = r.get("rag_mode", "unknown")
        diff = _get_difficulty(r)
        if diff is not None:
            nested[mode][diff].append(r)

    table: dict[str, dict[int, dict[str, Any]]] = {}
    for mode, by_diff in nested.items():
        table[mode] = {}
        for diff, rows in by_diff.items():
            table[mode][diff] = {"n": len(rows)}
            for m in METRIC_COLS:
                table[mode][diff][m] = _avg([r.get(m) for r in rows])
    return table


def _print_summary_table(summary: dict[str, dict[str, Any]]) -> None:
    metrics = ["faithfulness", "answer_relevance", "context_recall", "token_f1", "latency_ms"]
    header = f"{'rag_mode':<22}" + "".join(f"{m:>18}" for m in metrics) + f"{'n':>6}"
    sep = "=" * len(header)
    print(f"\n{sep}\nSUMMARY BY RAG MODE\n{sep}")
    print(header)
    print(sep)
    for mode in RAG_MODES:
        if mode not in summary:
            continue
        row = summary[mode]
        line = f"{mode:<22}"
        for m in metrics:
            v = row.get(m)
            line += f"{v:>18.4f}" if v is not None else f"{'N/A':>18}"
        line += f"{row['n']:>6}"
        print(line)
    print(sep)


def _print_difficulty_table(
    diff_table: dict[str, dict[int, dict[str, Any]]], metric: str = PRIMARY_METRIC
) -> None:
    diffs = sorted(DIFFICULTY_LABELS.keys())
    col_w = 14
    header = f"{'rag_mode':<22}" + "".join(f"{DIFFICULTY_LABELS[d]:>{col_w}}" for d in diffs)
    sep = "=" * len(header)
    print(f"\n{sep}\n{metric.upper()} BY DIFFICULTY\n{sep}")
    print(header)
    print(sep)
    for mode in RAG_MODES:
        if mode not in diff_table:
            continue
        line = f"{mode:<22}"
        for d in diffs:
            v = diff_table[mode].get(d, {}).get(metric)
            line += f"{v:>{col_w}.4f}" if v is not None else f"{'N/A':>{col_w}}"
        print(line)
    print(sep)


def _print_agentic_delta(
    diff_table: dict[str, dict[int, dict[str, Any]]], metric: str = PRIMARY_METRIC
) -> None:
    if "vanilla" not in diff_table:
        return
    diffs = sorted(DIFFICULTY_LABELS.keys())
    col_w = 14
    header = f"{'mode (Δ vs vanilla)':<26}" + "".join(
        f"{DIFFICULTY_LABELS[d]:>{col_w}}" for d in diffs
    )
    sep = "=" * len(header)
    print(f"\n{sep}\n{metric.upper()} DELTA (mode - vanilla) PER DIFFICULTY\n{sep}")
    print(header)
    print(sep)
    for mode in AGENTIC_MODES:
        if mode not in diff_table:
            continue
        line = f"{mode:<26}"
        for d in diffs:
            v = diff_table[mode].get(d, {}).get(metric)
            baseline = diff_table["vanilla"].get(d, {}).get(metric)
            if v is not None and baseline is not None:
                delta = v - baseline
                sign = "+" if delta >= 0 else ""
                line += f"{sign}{delta:>{col_w - 1}.4f}"
            else:
                line += f"{'N/A':>{col_w}}"
        print(line)
    print(sep)


def _save_csv(summary: dict, diff_table: dict, output_dir: Path) -> None:
    try:
        import pandas as pd  # type: ignore[import]
    except ImportError:
        print("[WARN] pandas not installed — skipping CSV output")
        return

    # Summary CSV
    rows_s = []
    for mode in RAG_MODES:
        if mode not in summary:
            continue
        row = {"rag_mode": mode, **summary[mode]}
        rows_s.append(row)
    pd.DataFrame(rows_s).to_csv(output_dir / "ddi_summary.csv", index=False)

    # Per-difficulty CSV
    rows_d = []
    for mode in RAG_MODES:
        if mode not in diff_table:
            continue
        for diff, metrics in diff_table[mode].items():
            rows_d.append(
                {
                    "rag_mode": mode,
                    "difficulty": diff,
                    "difficulty_label": DIFFICULTY_LABELS.get(diff, str(diff)),
                    **metrics,
                }
            )
    pd.DataFrame(rows_d).to_csv(output_dir / "ddi_by_difficulty.csv", index=False)
    print(f"CSV files saved → {output_dir}/ddi_summary.csv, ddi_by_difficulty.csv")


def _save_plots(
    summary: dict,
    diff_table: dict,
    output_dir: Path,
    metric: str = PRIMARY_METRIC,
) -> None:
    try:
        import matplotlib.pyplot as plt  # type: ignore[import]
        import numpy as np  # type: ignore[import]
        import pandas as pd  # type: ignore[import]
        import seaborn as sns  # type: ignore[import]
    except ImportError:
        print("[WARN] matplotlib/seaborn/numpy not installed — skipping plots")
        return

    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid", font_scale=1.1)

    available_modes = [m for m in RAG_MODES if m in diff_table]
    diffs = sorted(DIFFICULTY_LABELS.keys())

    # ── 1. Heatmap: rag_mode × difficulty for primary metric ──────────────────
    matrix = []
    for mode in available_modes:
        row = [diff_table[mode].get(d, {}).get(metric) for d in diffs]
        matrix.append(row)

    df_heat = pd.DataFrame(
        matrix,
        index=[RAG_MODE_LABELS.get(m, m) for m in available_modes],
        columns=[DIFFICULTY_LABELS[d] for d in diffs],
    )
    fig, ax = plt.subplots(figsize=(10, max(4, len(available_modes) * 0.7)))
    sns.heatmap(
        df_heat,
        annot=True,
        fmt=".3f",
        cmap="YlOrRd",
        vmin=0,
        vmax=1,
        ax=ax,
        linewidths=0.5,
    )
    ax.set_title(f"{metric.replace('_', ' ').title()} — DDI Benchmark", fontsize=14)
    ax.set_xlabel("Difficulty Level")
    ax.set_ylabel("RAG Mode")
    plt.tight_layout()
    plt.savefig(plots_dir / "ddi_heatmap.png", dpi=150)
    plt.close()

    # ── 2. Bar chart: per difficulty, grouped by mode ─────────────────────────
    x = np.arange(len(diffs))
    width = 0.8 / max(len(available_modes), 1)
    fig, ax = plt.subplots(figsize=(14, 6))
    for i, mode in enumerate(available_modes):
        vals = [diff_table[mode].get(d, {}).get(metric) for d in diffs]
        vals_clean = [v if v is not None else 0 for v in vals]
        offset = (i - len(available_modes) / 2 + 0.5) * width
        ax.bar(x + offset, vals_clean, width, label=RAG_MODE_LABELS.get(mode, mode), alpha=0.85)

    ax.set_xlabel("Difficulty Level")
    ax.set_ylabel(metric.replace("_", " ").title())
    ax.set_title(f"{metric.replace('_', ' ').title()} by Difficulty — DDI Benchmark")
    ax.set_xticks(x)
    ax.set_xticklabels([DIFFICULTY_LABELS[d] for d in diffs])
    ax.set_ylim(0, 1.05)
    ax.legend(loc="upper right", ncol=2, fontsize=9)
    plt.tight_layout()
    plt.savefig(plots_dir / "ddi_difficulty_bar.png", dpi=150)
    plt.close()

    # ── 3. Delta chart: agentic vs vanilla per difficulty ─────────────────────
    if "vanilla" in diff_table:
        fig, ax = plt.subplots(figsize=(12, 5))
        colors = plt.cm.Set2.colors  # type: ignore[attr-defined]
        agentic = [m for m in AGENTIC_MODES if m in diff_table]
        for i, mode in enumerate(agentic):
            deltas = []
            for d in diffs:
                v = diff_table[mode].get(d, {}).get(metric)
                base = diff_table["vanilla"].get(d, {}).get(metric)
                deltas.append((v - base) if v is not None and base is not None else 0)
            ax.plot(
                [DIFFICULTY_LABELS[d] for d in diffs],
                deltas,
                marker="o",
                label=RAG_MODE_LABELS.get(mode, mode),
                color=colors[i % len(colors)],
                linewidth=2,
            )
        ax.axhline(0, color="gray", linewidth=1, linestyle="--")
        ax.set_xlabel("Difficulty Level")
        ax.set_ylabel(f"Δ {metric.replace('_', ' ').title()} vs Vanilla")
        ax.set_title("Agentic RAG Modes — Advantage over Vanilla by Difficulty")
        ax.legend()
        plt.tight_layout()
        plt.savefig(plots_dir / "ddi_agentic_vs_vanilla.png", dpi=150)
        plt.close()

    # ── 4. Radar chart: all modes on 5 metrics ─────────────────────────────
    radar_metrics = ["faithfulness", "answer_relevance", "context_recall", "token_f1", "rouge_l"]
    available_radar = [
        m for m in radar_metrics if any(summary.get(mode, {}).get(m) for mode in available_modes)
    ]
    if len(available_radar) >= 3:
        angles = np.linspace(0, 2 * np.pi, len(available_radar), endpoint=False).tolist()
        angles += angles[:1]
        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={"polar": True})
        colors = plt.cm.tab10.colors  # type: ignore[attr-defined]
        for i, mode in enumerate(available_modes):
            vals = [summary[mode].get(m) or 0 for m in available_radar]
            vals += vals[:1]
            ax.plot(
                angles,
                vals,
                color=colors[i % len(colors)],
                linewidth=1.5,
                label=RAG_MODE_LABELS.get(mode, mode),
            )
            ax.fill(angles, vals, color=colors[i % len(colors)], alpha=0.05)
        ax.set_thetagrids(
            [a * 180 / np.pi for a in angles[:-1]],
            [m.replace("_", " ").title() for m in available_radar],
        )
        ax.set_ylim(0, 1)
        ax.set_title("DDI Benchmark — All Modes Radar", y=1.08)
        ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.1), fontsize=9)
        plt.tight_layout()
        plt.savefig(plots_dir / "ddi_radar.png", dpi=150, bbox_inches="tight")
        plt.close()

    print(f"Plots saved → {plots_dir}/")


def main() -> None:
    args = _parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading results from {args.input}…")
    results = _load_results(args.input)
    print(f"  {len(results)} valid results loaded")

    if not results:
        raise SystemExit("No valid results found.")

    results = _enrich_from_mongo(results, args.mongo_uri, args.project_id)

    summary = _build_summary(results)
    diff_table = _build_difficulty_table(results)

    _print_summary_table(summary)
    _print_difficulty_table(diff_table, metric=PRIMARY_METRIC)
    _print_agentic_delta(diff_table, metric=PRIMARY_METRIC)

    _save_csv(summary, diff_table, output_dir)
    _save_plots(summary, diff_table, output_dir, metric=PRIMARY_METRIC)

    print(f"\nDone. Results in {output_dir}/")


if __name__ == "__main__":
    main()
