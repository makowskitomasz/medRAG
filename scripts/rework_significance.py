#!/usr/bin/env python3
"""Paired significance analysis for the rework benchmarks (HotpotQA + DDI).

Metrics are read from MongoDB rather than the results JSON: the run files accumulated
duplicate and stale records across resumes, whereas Mongo holds every judged answer with a
timestamp. For each (rag_mode, question) we take the newest eval_result inside the run's
time window — the same latest-wins rule the exporters use.

Within one run every mode answers the same questions, so `mode - vanilla` is a paired
contrast. Vanilla is the untouched control: it absorbs question-sample and judge effects,
which then cancel from the contrast. Cross-run comparison to the June baseline is reported
only where the vanilla control reproduces (HotpotQA); for DDI it does not, so only the
within-run contrast is valid there.

Data is fetched by a companion mongosh call (see rework_analysis.sh) and passed in as JSON
on stdin: {domain: {mode: {question: {faithfulness, answer_correctness}}}}.
"""

import json
import sys

import numpy as np
from scipy import stats

MODES = ["vanilla", "iterative_multihop", "multi_agent", "madam_rag", "rare_rag"]
METRICS = ["faithfulness", "answer_correctness"]
_BOOTSTRAP_N = 10_000
_SEED = 0


def _paired(a: dict, b: dict, metric: str) -> tuple[np.ndarray, np.ndarray]:
    shared = sorted(
        q for q in set(a) & set(b) if a[q].get(metric) is not None and b[q].get(metric) is not None
    )
    return (
        np.array([a[q][metric] for q in shared]),
        np.array([b[q][metric] for q in shared]),
    )


def _ci(diff: np.ndarray) -> tuple[float, float]:
    rng = np.random.default_rng(_SEED)
    means = rng.choice(diff, size=(_BOOTSTRAP_N, diff.size), replace=True).mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def _stars(p: float) -> str:
    return "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "n.s."


def _contrast(van: np.ndarray, mod: np.ndarray) -> tuple[float, float, tuple[float, float], int]:
    diff = mod - van
    if diff.size == 0 or np.allclose(diff, 0):
        return 0.0, 1.0, (0.0, 0.0), diff.size
    p = float(stats.wilcoxon(van, mod, zero_method="wilcox").pvalue)
    return float(diff.mean()), p, _ci(diff), diff.size


def _domain(run: dict, label: str) -> None:
    print(f"\n{'=' * 78}\n{label}\n{'=' * 78}")
    for metric in METRICS:
        print(f"\n  {metric} — mean per mode, and paired advantage over vanilla:")
        print(f"  {'mode':<20}{'mean':>8}{'Δ vs van':>10}{'95% CI':>20}{'p':>9}{'sig':>6}{'n':>5}")
        van = run.get("vanilla", {})
        van_mean = np.mean([v[metric] for v in van.values() if v.get(metric) is not None])
        for mode in MODES:
            if mode not in run:
                continue
            vals = [v[metric] for v in run[mode].values() if v.get(metric) is not None]
            mean = np.mean(vals) if vals else float("nan")
            if mode == "vanilla":
                print(f"  {mode:<20}{mean:>8.3f}{'—  (control)':>40}")
                continue
            a, b = _paired(van, run[mode], metric)
            d, p, (lo, hi), n = _contrast(a, b)
            ci = f"[{lo:+.3f}, {hi:+.3f}]"
            print(f"  {mode:<20}{mean:>8.3f}{d:>+10.3f}{ci:>20}{p:>9.4f}{_stars(p):>6}{n:>5}")
        print(f"  {'(vanilla mean':<20}{van_mean:>8.3f})")


def main() -> None:
    data = json.load(sys.stdin)
    if "hotpot" in data:
        _domain(data["hotpot"], "HotpotQA (1000 questions, encyclopedic multi-hop)")
    if "ddi" in data:
        _domain(data["ddi"], "DDI (100 questions, drug-interaction advisory)")


if __name__ == "__main__":
    main()
