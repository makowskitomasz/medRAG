#!/usr/bin/env python3
"""
Prepare Dataset A: HotpotQA (multi-hop Wikipedia reasoning).

Downloads hotpot_qa/distractor validation split, samples 1000 QA pairs
(400 easy + 600 hard), and exports:
  - data/hotpotqa_1000.json    — list of QA pairs for the benchmark runner
  - data/hotpotqa_docs/        — one .txt per unique Wikipedia article (for ingestion)

HotpotQA requires synthesizing information from TWO Wikipedia articles per
question, which differentiates RAG modes (vanilla vs iterative_multihop etc.)
much better than SQuAD's single-context extractive format.

Usage:
    python scripts/prepare_hotpotqa.py
    python scripts/prepare_hotpotqa.py --easy-count 200 --hard-count 300 --output-dir /tmp/data
"""

import argparse
import json
import random
import re
from pathlib import Path


def _slug(text: str, max_len: int = 80) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return s[:max_len]


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Prepare HotpotQA dataset for medRAG benchmark")
    p.add_argument(
        "--output-dir",
        default="data",
        help="Root output directory (default: data/)",
    )
    p.add_argument(
        "--easy-count",
        type=int,
        default=400,
        help="Number of 'easy' samples to include (default: 400)",
    )
    p.add_argument(
        "--hard-count",
        type=int,
        default=600,
        help="Number of 'hard' samples to include (default: 600)",
    )
    p.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible sampling (default: 42)",
    )
    return p.parse_args()


def _extract_supporting_docs(row: dict) -> list[dict]:
    """Return only the 2 relevant supporting documents, not all ~10 distractors."""
    supporting_titles: set[str] = set(row["supporting_facts"]["title"])
    titles: list[str] = row["context"]["title"]
    sentences: list[list[str]] = row["context"]["sentences"]
    return [
        {"title": titles[i], "sentences": sentences[i]}
        for i in range(len(titles))
        if titles[i] in supporting_titles
    ]


def main() -> None:
    args = _parse_args()

    try:
        from datasets import load_dataset  # type: ignore[import]
    except ImportError as exc:
        raise SystemExit("Run: source scripts/.venv/bin/activate (or uv sync in scripts/)") from exc

    output_dir = Path(args.output_dir)
    docs_dir = output_dir / "hotpotqa_docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    print("Loading hotpotqa/hotpot_qa distractor validation split…")
    ds = load_dataset("hotpotqa/hotpot_qa", "distractor", split="validation")
    rows = list(ds)  # type: ignore[arg-type]
    print(f"  Total rows: {len(rows)}")

    rng = random.Random(args.seed)

    by_level: dict[str, list] = {}
    for r in rows:
        by_level.setdefault(r["level"], []).append(r)

    counts = {lvl: len(v) for lvl, v in by_level.items()}
    print(f"  Levels: {counts}")

    total = args.easy_count + args.hard_count
    # Try stratified sampling: easy + hard. Fall back to proportional if levels missing.
    easy_rows = by_level.get("easy", [])
    hard_rows = by_level.get("hard", [])
    medium_rows = by_level.get("medium", [])

    easy_sample = rng.sample(easy_rows, min(args.easy_count, len(easy_rows)))
    hard_sample = rng.sample(hard_rows, min(args.hard_count, len(hard_rows)))

    combined = easy_sample + hard_sample

    # If we don't have enough, fill from medium then remaining levels
    deficit = total - len(combined)
    if deficit > 0:
        fill_pool = medium_rows + [r for r in rows if r not in combined]
        fill = rng.sample(fill_pool, min(deficit, len(fill_pool)))
        combined += fill
        print(f"  Filled {len(fill)} missing samples from other levels")

    rng.shuffle(combined)
    level_counts = {lvl: sum(1 for r in combined if r["level"] == lvl) for lvl in counts}
    print(f"  Sampled: {level_counts} = {len(combined)} total")

    qa_pairs: list[dict] = []
    seen_titles: dict[str, str] = {}  # title → filename

    for row in combined:
        supporting_docs = _extract_supporting_docs(row)

        # Write each unique article to docs_dir
        for doc in supporting_docs:
            title: str = doc["title"]
            if title not in seen_titles:
                fname = _slug(title) + ".txt"
                # Avoid filename collision for different titles with same slug
                target = docs_dir / fname
                idx = 1
                while (
                    target.exists() and target.read_text(encoding="utf-8").split("\n")[0] != title
                ):
                    fname = f"{_slug(title)}_{idx}.txt"
                    target = docs_dir / fname
                    idx += 1
                content = f"{title}\n\n{' '.join(doc['sentences'])}\n"
                target.write_text(content, encoding="utf-8")
                seen_titles[title] = fname

        qa_pairs.append(
            {
                "question": row["question"],
                "gold_answer": row["answer"],
                "supporting_docs": supporting_docs,
                "level": row["level"],
                "type": row["type"],
                "metadata": {
                    "source": "hotpotqa",
                    "id": row["id"],
                },
            }
        )

    qa_path = output_dir / "hotpotqa_1000.json"
    qa_path.write_text(json.dumps(qa_pairs, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\nOutputs:")
    print(f"  QA pairs:  {qa_path}  ({len(qa_pairs)} items)")
    print(f"  Documents: {docs_dir}/  ({len(seen_titles)} unique articles)")


if __name__ == "__main__":
    main()
