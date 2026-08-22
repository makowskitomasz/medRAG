#!/usr/bin/env python3
"""Paired significance tests for the DDI benchmark.

Within one run every RAG mode answers the same 100 questions, so `mode - vanilla` is a
paired contrast. Vanilla is the control: its code was not touched by the pipeline rewrite,
so anything that shifts vanilla (question sample, judge behaviour) shifts every mode with
it and cancels out of the contrast.

Across runs there is no pairing: the old and the new run used *different* DDI question
samples (both stratified 20-per-difficulty-level, but drawn independently). Absolute means
are therefore NOT comparable between runs — only the vanilla-relative advantages are, and
even those compare two samples rather than repeated measures.
"""

import argparse
import json
from pathlib import Path

import numpy as np
from scipy import stats

MODES = ["vanilla", "iterative_multihop", "multi_agent", "madam_rag", "rare_rag"]
METRIC = "faithfulness"
_BOOTSTRAP_N = 10_000
_RNG_SEED = 0


def _load(path: Path) -> dict[str, dict[str, float]]:
    """{rag_mode: {question: metric}} — keeps only records that carry the metric."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload["results"] if isinstance(payload, dict) else payload
    out: dict[str, dict[str, float]] = {}
    for r in records:
        if r.get(METRIC) is None:
            continue
        out.setdefault(r["rag_mode"], {})[r["question"].strip()] = float(r[METRIC])
    return out


def _paired(a: dict[str, float], b: dict[str, float]) -> tuple[np.ndarray, np.ndarray]:
    shared = sorted(set(a) & set(b))
    return np.array([a[q] for q in shared]), np.array([b[q] for q in shared])


def _ci(diff: np.ndarray) -> tuple[float, float]:
    """Bootstrap 95% CI of the mean paired difference."""
    rng = np.random.default_rng(_RNG_SEED)
    means = rng.choice(diff, size=(_BOOTSTRAP_N, diff.size), replace=True).mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def _test(a: np.ndarray, b: np.ndarray) -> tuple[float, float, tuple[float, float], int]:
    """Returns (mean diff b-a, wilcoxon p, bootstrap CI, n)."""
    diff = b - a
    if np.allclose(diff, 0):
        return 0.0, 1.0, (0.0, 0.0), diff.size
    p = float(stats.wilcoxon(a, b, zero_method="wilcox").pvalue)
    return float(diff.mean()), p, _ci(diff), diff.size


def _stars(p: float) -> str:
    return "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "n.s."


def _advantage_over_vanilla(run: dict[str, dict[str, float]], label: str) -> dict[str, float]:
    print(f"\n{label}: mode − vanilla (paired, within run)")
    print(f"{'mode':<20}{'Δ':>9}{'95% CI':>20}{'p':>10}{'sig':>7}{'n':>5}")
    means: dict[str, float] = {}
    for mode in MODES:
        if mode == "vanilla" or mode not in run:
            continue
        van, mod = _paired(run["vanilla"], run[mode])
        d, p, (lo, hi), n = _test(van, mod)
        means[mode] = d
        print(f"{mode:<20}{d:>+9.3f}{f'[{lo:+.3f}, {hi:+.3f}]':>20}{p:>10.4f}{_stars(p):>7}{n:>5}")
    return means


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", default="results/ddi_results.json")
    ap.add_argument("--new", default="results/ddi_results_rework_enriched.json")
    args = ap.parse_args()

    old, new = _load(Path(args.old)), _load(Path(args.new))

    shared = set(old.get("vanilla", {})) & set(new.get("vanilla", {}))
    print("=" * 72)
    print("1. Cross-run pairing check")
    print("=" * 72)
    print(f"questions shared between the two runs: {len(shared)}")
    if not shared:
        print("→ disjoint question samples: absolute means are NOT comparable across runs.")
        print("  Report only the within-run contrasts below.")

    print("\n" + "=" * 72)
    print("2. CONTROLLED: advantage over vanilla, computed inside each run")
    print("=" * 72)
    adv_old = _advantage_over_vanilla(old, "OLD run")
    adv_new = _advantage_over_vanilla(new, "NEW run")

    print("\nChange in advantage-over-vanilla (new − old); different question samples,")
    print("so this indicates the direction of the rewrite's effect, not a tested effect size.")
    print(f"{'mode':<20}{'old adv':>10}{'new adv':>10}{'change':>10}")
    for mode in MODES:
        if mode in adv_old and mode in adv_new:
            print(
                f"{mode:<20}{adv_old[mode]:>+10.3f}{adv_new[mode]:>+10.3f}"
                f"{adv_new[mode] - adv_old[mode]:>+10.3f}"
            )

    print(
        "\nVanilla (unchanged code) across runs: "
        f"{np.mean(list(old['vanilla'].values())):.3f} → "
        f"{np.mean(list(new['vanilla'].values())):.3f} "
        "— reflects the different question sample, not a code change."
    )


if __name__ == "__main__":
    main()
