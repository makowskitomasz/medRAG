#!/usr/bin/env python3
"""
Generate QA pairs for DrugBank interactions using an LLM via OpenRouter.

Reads:   data/drugbank_interactions.json
Writes:  data/drugbank_qa.json

Usage:
    python scripts/generate_drugbank_qa.py
    python scripts/generate_drugbank_qa.py --max-interactions 50 --dry-run

Required env var:
    OPENROUTER_API_KEY
"""

import argparse
import json
import os
import re
import time
from pathlib import Path

# Interactions that must appear first in the output
_PRIORITY_PAIRS: list[tuple[str, str]] = [
    ("warfarin", "aspirin"),
    ("warfarin", "nsaid"),
    ("statin", "cyp3a4"),
    ("ace inhibitor", "potassium"),
    ("metformin", "contrast"),
    ("ssri", "maoi"),
    ("clopidogrel", "ppi"),
    ("digoxin", "amiodarone"),
]

_SYSTEM_PROMPT = (
    "You are a clinical pharmacology expert. "
    "Generate exactly 5 QA pairs about a drug interaction as a JSON array. "
    "Each item must have keys 'question' and 'gold_answer'. "
    "Focus on: risk, mechanism, monitoring, contraindication. "
    "Answers must be 1–2 sentences, strictly derived from the provided text. "
    "Return ONLY valid JSON — no markdown, no explanation."
)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate DrugBank QA pairs via OpenRouter LLM")
    p.add_argument(
        "--input",
        default="data/drugbank_interactions.json",
        help="Path to drugbank_interactions.json",
    )
    p.add_argument(
        "--output",
        default="data/drugbank_qa.json",
        help="Path to output drugbank_qa.json",
    )
    p.add_argument(
        "--max-interactions",
        type=int,
        default=None,
        help="Limit number of interactions to process (default: all)",
    )
    p.add_argument(
        "--model",
        default="anthropic/claude-haiku-4-5",
        help="OpenRouter model to use (default: anthropic/claude-haiku-4-5)",
    )
    p.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Seconds to sleep between API calls to avoid rate-limits (default: 0.5)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Process only the 8 priority pairs without calling the API",
    )
    return p.parse_args()


def _is_priority(drug1: str, drug2: str) -> bool:
    d1 = drug1.lower()
    d2 = drug2.lower()
    return any((a in d1 or a in d2) and (b in d1 or b in d2) for a, b in _PRIORITY_PAIRS)


def _sort_interactions(interactions: list[dict]) -> list[dict]:
    priority = [r for r in interactions if _is_priority(r["drug1"], r["drug2"])]
    rest = [r for r in interactions if not _is_priority(r["drug1"], r["drug2"])]
    return priority + rest


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _generate_qa(client, model: str, interaction: dict) -> list[dict]:
    text = f"Interaction: {interaction['drug1']} + {interaction['drug2']}\n{interaction['description']}"
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        temperature=0.2,
        max_tokens=1024,
    )
    raw = response.choices[0].message.content or ""
    cleaned = _strip_fences(raw)
    pairs = json.loads(cleaned)
    if not isinstance(pairs, list):
        raise ValueError(f"Expected JSON array, got: {type(pairs)}")
    return pairs


def main() -> None:
    args = _parse_args()

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key and not args.dry_run:
        raise SystemExit("OPENROUTER_API_KEY env var is required (or use --dry-run)")

    interactions: list[dict] = json.loads(Path(args.input).read_text(encoding="utf-8"))
    interactions = _sort_interactions(interactions)

    if args.dry_run:
        interactions = [r for r in interactions if _is_priority(r["drug1"], r["drug2"])]
        print(f"[dry-run] Processing {len(interactions)} priority interactions only")

    if args.max_interactions:
        interactions = interactions[: args.max_interactions]

    print(f"Interactions to process: {len(interactions)}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        # Build dummy QA pairs without calling the API
        all_pairs: list[dict] = []
        for ix in interactions:
            dummy = {
                "question": f"What is the interaction between {ix['drug1']} and {ix['drug2']}?",
                "gold_answer": ix["description"][:200],
                "metadata": {
                    "drugs": [ix["drug1"], ix["drug2"]],
                    "category": "interaction",
                },
            }
            all_pairs.append(dummy)
        output_path.write_text(json.dumps(all_pairs, indent=2, ensure_ascii=False))
        print(f"[dry-run] Wrote {len(all_pairs)} dummy pairs → {output_path}")
        return

    try:
        from openai import OpenAI  # type: ignore[import]
    except ImportError:
        raise SystemExit("Install openai: uv add openai") from None

    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
    )

    all_pairs: list[dict] = []
    errors = 0

    for i, ix in enumerate(interactions, 1):
        label = f"{ix['drug1']} + {ix['drug2']}"
        print(f"  [{i}/{len(interactions)}] {label[:60]}…", end=" ", flush=True)
        try:
            pairs = _generate_qa(client, args.model, ix)
            enriched = [
                {
                    "question": p.get("question", ""),
                    "gold_answer": p.get("gold_answer", ""),
                    "metadata": {
                        "drugs": [ix["drug1"], ix["drug2"]],
                        "category": "interaction",
                    },
                }
                for p in pairs
                if p.get("question")
            ]
            all_pairs.extend(enriched)
            print(f"✓ {len(enriched)} pairs")
        except Exception as exc:
            errors += 1
            print(f"✗ {exc}")

        # Incremental save after every interaction
        output_path.write_text(json.dumps(all_pairs, indent=2, ensure_ascii=False))

        if args.delay > 0:
            time.sleep(args.delay)

    print(f"\nDone: {len(all_pairs)} QA pairs, {errors} errors")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()
