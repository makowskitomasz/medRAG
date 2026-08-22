"""Final thesis analysis: nine RAG modes on HotpotQA and DDI.

The four rewritten modes (multi_agent, iterative_multihop, madam_rag, rare_rag) were
re-evaluated in July on the same question sets used by the June run of the five
untouched modes (vanilla, hyde, query_rewriting, self_reflection, corrective_rag).
Per-question metrics come from MongoDB `eval_results` (latest-per-question inside each
run window); the exported JSON files dropped null metrics and cannot be used directly.

Vanilla is the control: every mode is compared against it paired per question with a
Wilcoxon signed-rank test and a bootstrap CI on the mean difference.

Usage: uv run --with scipy --with numpy --with pymongo python scripts/thesis_final_analysis.py
"""

from __future__ import annotations

import csv
import statistics as st
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np
from pymongo import MongoClient
from scipy.stats import wilcoxon

MONGO_URI = "mongodb://localhost:27017/medrag"
OUT_DIR = Path("results/thesis_final")

UNTOUCHED = ["vanilla", "hyde", "query_rewriting", "self_reflection", "corrective_rag"]
REWRITTEN = ["multi_agent", "iterative_multihop", "madam_rag", "rare_rag"]
ORDER = UNTOUCHED + REWRITTEN

# Run windows: the June benchmark for the untouched modes, the July re-run for the
# rewritten ones. Both cover the same question sets.
WINDOWS = {
    "hotpotqa": {
        "untouched": (datetime(2026, 6, 4), datetime(2026, 6, 8)),
        "rewritten": (datetime(2026, 7, 10), datetime(2026, 7, 13)),
    },
    "ddi": {
        "untouched": (datetime(2026, 6, 9), datetime(2026, 6, 11)),
        "rewritten": (datetime(2026, 7, 11), datetime(2026, 7, 13)),
    },
}

METRICS = [
    "token_f1",
    "em",
    "rouge_l",
    "faithfulness",
    "answer_correctness",
    "answer_relevance",
    "context_recall",
    "latency_ms",
]

RNG = np.random.default_rng(0)


def stars(p: float) -> str:
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return "n.s."


def load(db, questions: list[str], windows: dict) -> dict[str, dict[str, dict]]:
    """mode -> question -> metrics, taking the latest evaluation per question."""
    rec: dict[str, dict[str, dict]] = defaultdict(dict)
    for group, modes in (("untouched", UNTOUCHED), ("rewritten", REWRITTEN)):
        lo, hi = windows[group]
        cursor = db.eval_results.find(
            {
                "question": {"$in": questions},
                "rag_mode": {"$in": modes},
                "timestamp": {"$gte": lo, "$lt": hi},
                "metrics.faithfulness": {"$ne": None},
            },
            {"question": 1, "rag_mode": 1, "metrics": 1, "timestamp": 1},
        ).sort("timestamp", 1)
        for doc in cursor:
            rec[doc["rag_mode"]][doc["question"].strip()] = doc["metrics"]
    return rec


def mean(rec, mode: str, metric: str) -> tuple[float, int]:
    vals = [m[metric] for m in rec[mode].values() if m.get(metric) is not None]
    return (st.mean(vals), len(vals)) if vals else (float("nan"), 0)


def paired(rec, mode: str, metric: str, keep=None) -> tuple[float, float, int, float, float]:
    """Mean difference vs vanilla, Wilcoxon p, n, and a bootstrap 95% CI."""
    van = rec["vanilla"]
    qs = [
        q
        for q in rec[mode]
        if q in van
        and rec[mode][q].get(metric) is not None
        and van[q].get(metric) is not None
        and (keep is None or keep(q))
    ]
    if not qs:
        return float("nan"), 1.0, 0, float("nan"), float("nan")
    a = np.array([rec[mode][q][metric] for q in qs], dtype=float)
    b = np.array([van[q][metric] for q in qs], dtype=float)
    d = a - b
    if np.all(d == 0):
        return 0.0, 1.0, len(qs), 0.0, 0.0
    p = float(wilcoxon(a, b).pvalue)
    boot = [RNG.choice(d, len(d), replace=True).mean() for _ in range(10_000)]
    return (
        float(d.mean()),
        p,
        len(qs),
        float(np.percentile(boot, 2.5)),
        float(np.percentile(boot, 97.5)),
    )


def report(name: str, rec, levels: dict[str, int] | None, out) -> None:
    def w(line: str = "") -> None:
        print(line)
        out.write(line + "\n")

    w("=" * 78)
    w(f"{name} — nine RAG modes, same questions. (*) = rewritten in July.")
    w("=" * 78)
    header = f"{'mode':<19}" + "".join(f"{m[:7]:>9}" for m in METRICS) + f"{'n':>6}"
    w(header)
    for mode in ORDER:
        row = f"{mode + ('*' if mode in REWRITTEN else ''):<19}"
        for metric in METRICS:
            v, _ = mean(rec, mode, metric)
            if metric == "latency_ms":
                v = v / 1000
            row += f"{v:>9.3f}" if v == v else f"{'-':>9}"
        row += f"{mean(rec, mode, 'faithfulness')[1]:>6}"
        w(row)

    for metric in ("faithfulness", "answer_correctness", "token_f1"):
        w()
        w(f"--- paired advantage over Vanilla — {metric}")
        w(f"{'mode':<19}{'delta':>9}{'p':>10}   {'95% CI':<19}{'n':>6}  sig")
        for mode in ORDER[1:]:
            d, p, n, lo, hi = paired(rec, mode, metric)
            if n == 0:
                continue
            w(f"{mode:<19}{d:>+9.3f}{p:>10.4f}   [{lo:>+6.3f},{hi:>+6.3f}]{n:>6}  {stars(p)}")

    if levels is None:
        return

    for metric in ("faithfulness", "answer_correctness"):
        w()
        w(f"--- by difficulty level — {metric}")
        w(f"{'mode':<19}" + "".join(f"{'L' + str(i):>9}" for i in range(1, 6)))
        for mode in ORDER:
            row = f"{mode:<19}"
            for lvl in range(1, 6):
                vals = [
                    m[metric]
                    for q, m in rec[mode].items()
                    if levels.get(q) == lvl and m.get(metric) is not None
                ]
                row += f"{st.mean(vals):>9.3f}" if vals else f"{'-':>9}"
            w(row)

    hard = lambda q: levels.get(q) in (4, 5)  # noqa: E731
    for metric in ("faithfulness", "answer_correctness"):
        w()
        w(f"--- hard subset (L4+L5) paired vs Vanilla — {metric}")
        for mode in ORDER[1:]:
            d, p, n, lo, hi = paired(rec, mode, metric, keep=hard)
            if n == 0:
                continue
            w(f"{mode:<19}{d:>+9.3f}{p:>10.4f}   [{lo:>+6.3f},{hi:>+6.3f}]{n:>6}  {stars(p)}")


def write_csv(path: Path, rec, levels: dict[str, int] | None) -> None:
    with path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["rag_mode", "n", *METRICS, "delta_faith", "p_faith", "delta_corr", "p_corr"]
        )
        for mode in ORDER:
            row = [mode, mean(rec, mode, "faithfulness")[1]]
            row += [round(mean(rec, mode, m)[0], 4) for m in METRICS]
            if mode == "vanilla":
                row += ["", "", "", ""]
            else:
                df, pf, *_ = paired(rec, mode, "faithfulness")
                dc, pc, *_ = paired(rec, mode, "answer_correctness")
                row += [round(df, 4), round(pf, 4), round(dc, 4), round(pc, 4)]
            writer.writerow(row)
    if levels is None:
        return
    with path.with_name(path.stem + "_by_difficulty.csv").open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["rag_mode", "level", "n", "faithfulness", "answer_correctness"])
        for mode in ORDER:
            for lvl in range(1, 6):
                qs = [q for q, m in rec[mode].items() if levels.get(q) == lvl]
                if not qs:
                    continue
                f = [
                    rec[mode][q]["faithfulness"]
                    for q in qs
                    if rec[mode][q].get("faithfulness") is not None
                ]
                c = [
                    rec[mode][q]["answer_correctness"]
                    for q in qs
                    if rec[mode][q].get("answer_correctness") is not None
                ]
                writer.writerow(
                    [
                        mode,
                        lvl,
                        len(qs),
                        round(st.mean(f), 4) if f else "",
                        round(st.mean(c), 4) if c else "",
                    ]
                )


def main() -> None:
    import json

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    db = MongoClient(MONGO_URI).get_default_database()

    ddi_rows = json.loads(Path("results/slim/ddi_baseline_metrics.json").read_text())["results"]
    ddi_levels = {r["question"].strip(): r["level"] for r in ddi_rows}
    ddi_qs = sorted(ddi_levels)

    hp_rows = json.loads(Path("results/slim/hotpotqa_rework_metrics.json").read_text())["results"]
    hp_qs = sorted({r["question"].strip() for r in hp_rows})

    with (OUT_DIR / "significance.txt").open("w") as out:
        hp = load(db, hp_qs, WINDOWS["hotpotqa"])
        report("HotpotQA (1000 encyclopedic multi-hop questions)", hp, None, out)
        write_csv(OUT_DIR / "hotpotqa.csv", hp, None)

        out.write("\n\n")
        print()
        ddi = load(db, ddi_qs, WINDOWS["ddi"])
        report("DDI (100 stratified drug-interaction questions)", ddi, ddi_levels, out)
        write_csv(OUT_DIR / "ddi.csv", ddi, ddi_levels)

    print(f"\nwrote {OUT_DIR}/significance.txt, hotpotqa.csv, ddi.csv, ddi_by_difficulty.csv")


if __name__ == "__main__":
    main()
