#!/usr/bin/env python3
"""
Generate 100 QA pairs for the DDI benchmark using an LLM via OpenRouter.

Reads:
  data/ddi_interactions.json      — interaction records from prepare_ddi_corpus.py
  data/ddi_docs/drugs/            — drug profile .txt files from prepare_openfda.py

Writes:
  data/ddi_qa.json                — 100 QA pairs in medRAG benchmark format

QA types (configurable with --counts):
  A — multi-drug interaction:   "What happens when drug X is combined with drug Y?"
  B — patient profile:          "Patient aged N, condition C, taking drugs A,B — safe to add X?"
  C — mechanism:                "Which drugs interact with X via mechanism Y?"

Usage:
    python scripts/generate_ddi_qa.py --dry-run
    python scripts/generate_ddi_qa.py --counts 40,40,20
    python scripts/generate_ddi_qa.py --counts 10,5,5 --dry-run  # quick test

Required env var:
    OPENROUTER_API_KEY
"""

import argparse
import json
import os
import random
import re
import time
from pathlib import Path

_SYSTEM_INTERACTION = (
    "You are a clinical pharmacology expert. "
    "Given a drug-drug interaction text, generate a realistic clinical QA pair. "
    "Return ONLY a JSON object with keys 'question' and 'gold_answer'. "
    "Question: ask about risk, mechanism, or monitoring for the specific pair. "
    "Answer: 1-3 sentences strictly from the provided text. No markdown, no explanation."
)

_SYSTEM_PATIENT = (
    "You are a clinical pharmacology expert. "
    "Given one or more drug profiles, create a patient-scenario QA pair. "
    "Return ONLY a JSON object with keys 'question' and 'gold_answer'. "
    "Question: describe a patient (age, sex, condition, current medications) and ask whether "
    "adding a specific drug is safe. Use realistic demographics. "
    "Answer: 2-3 sentences grounded in the provided texts. No markdown, no explanation."
)

_SYSTEM_MECHANISM = (
    "You are a clinical pharmacology expert. "
    "Given drug interaction or profile text, generate a mechanism-focused QA pair. "
    "Return ONLY a JSON object with keys 'question' and 'gold_answer'. "
    "Question: ask about the pharmacokinetic or pharmacodynamic mechanism behind an interaction. "
    "Answer: 1-2 sentences from the provided text. No markdown, no explanation."
)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate DDI QA pairs for medRAG benchmark")
    p.add_argument(
        "--interactions",
        default="data/ddi_interactions.json",
        help="Path to ddi_interactions.json",
    )
    p.add_argument(
        "--drugs-dir",
        default="data/ddi_docs/drugs",
        help="Directory with per-drug .txt profiles",
    )
    p.add_argument(
        "--output",
        default="data/ddi_qa.json",
        help="Path to output QA JSON (default: data/ddi_qa.json)",
    )
    p.add_argument(
        "--counts",
        default="40,40,20",
        help="Comma-separated counts for types A,B,C (default: 40,40,20 = 100 total)",
    )
    p.add_argument(
        "--model",
        default="anthropic/claude-haiku-4-5",
        help="OpenRouter model (default: anthropic/claude-haiku-4-5)",
    )
    p.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Seconds between API calls (default: 0.5)",
    )
    p.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate dummy QA pairs without calling the API",
    )
    return p.parse_args()


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _call_llm(client, model: str, system: str, user: str) -> dict:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.3,
        max_tokens=512,
    )
    raw = response.choices[0].message.content or ""
    return json.loads(_strip_fences(raw))


def _dummy_pair(question: str, answer: str, qa_type: str, drugs: list[str]) -> dict:
    return {
        "question": question,
        "gold_answer": answer,
        "metadata": {"source": "ddi", "type": qa_type, "drugs": drugs},
    }


# Priority drug pairs to sample first (ensuring clinical relevance in top items)
_PRIORITY_DRUGS = {
    "warfarin",
    "aspirin",
    "amiodarone",
    "digoxin",
    "metformin",
    "simvastatin",
    "atorvastatin",
    "clopidogrel",
    "metoprolol",
    "lisinopril",
    "omeprazole",
    "fluoxetine",
    "sertraline",
}


def _prioritize(interactions: list[dict]) -> list[dict]:
    priority = [
        r
        for r in interactions
        if r["drug1"].lower() in _PRIORITY_DRUGS or r["drug2"].lower() in _PRIORITY_DRUGS
    ]
    rest = [r for r in interactions if r not in priority]
    return priority + rest


def _load_drug_profile(drugs_dir: Path, drug_name: str) -> str | None:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", drug_name).strip("_").lower()[:80]
    path = drugs_dir / f"{slug}.txt"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None


def _generate_type_a(
    client,
    model: str,
    record: dict,
    delay: float,
    dry_run: bool,
) -> dict | None:
    """Multi-drug interaction pair."""
    text = (
        f"Drug Interaction: {record['drug1']} + {record['drug2']}\n"
        f"Type: {record['interaction_type']}\n\n"
        f"{record['source_text'][:1500]}"
    )
    if dry_run:
        return _dummy_pair(
            f"What is the clinical significance of combining {record['drug1']} with {record['drug2']}?",
            record["source_text"][:200],
            "interaction",
            [record["drug1"], record["drug2"]],
        )
    try:
        pair = _call_llm(client, model, _SYSTEM_INTERACTION, text)
        pair["metadata"] = {
            "source": "ddi",
            "type": "interaction",
            "drugs": [record["drug1"], record["drug2"]],
        }
        if args.delay > 0:
            time.sleep(delay)
        return pair
    except Exception as exc:
        print(f"    ✗ type-A error: {exc}")
        return None


def _generate_type_b(
    client,
    model: str,
    record: dict,
    drugs_dir: Path,
    delay: float,
    dry_run: bool,
) -> dict | None:
    """Patient profile pair — uses drug profile file if available."""
    profile1 = _load_drug_profile(drugs_dir, record["drug1"])
    profile2 = _load_drug_profile(drugs_dir, record["drug2"])

    context_parts: list[str] = []
    if profile1:
        context_parts.append(profile1[:800])
    if profile2:
        context_parts.append(profile2[:800])
    # Fall back to interaction text when no profiles available
    if not context_parts:
        context_parts.append(record["source_text"][:1000])

    context = "\n\n---\n\n".join(context_parts)

    if dry_run:
        return _dummy_pair(
            f"A 65-year-old patient with hypertension is currently taking {record['drug1']}. "
            f"Is it safe to add {record['drug2']}?",
            record["source_text"][:200],
            "patient_profile",
            [record["drug1"], record["drug2"]],
        )
    try:
        pair = _call_llm(client, model, _SYSTEM_PATIENT, context)
        pair["metadata"] = {
            "source": "ddi",
            "type": "patient_profile",
            "drugs": [record["drug1"], record["drug2"]],
        }
        if delay > 0:
            time.sleep(delay)
        return pair
    except Exception as exc:
        print(f"    ✗ type-B error: {exc}")
        return None


def _generate_type_c(
    client,
    model: str,
    record: dict,
    delay: float,
    dry_run: bool,
) -> dict | None:
    """Mechanism-focused pair."""
    text = (
        f"Drug: {record['drug1']}\nInteracting with: {record['drug2']}\n"
        f"Interaction Type: {record['interaction_type']}\n\n"
        f"{record['source_text'][:1500]}"
    )
    if dry_run:
        return _dummy_pair(
            f"What is the pharmacokinetic mechanism behind the interaction between "
            f"{record['drug1']} and {record['drug2']}?",
            record["source_text"][:200],
            "mechanism",
            [record["drug1"], record["drug2"]],
        )
    try:
        pair = _call_llm(client, model, _SYSTEM_MECHANISM, text)
        pair["metadata"] = {
            "source": "ddi",
            "type": "mechanism",
            "drugs": [record["drug1"], record["drug2"]],
        }
        if delay > 0:
            time.sleep(delay)
        return pair
    except Exception as exc:
        print(f"    ✗ type-C error: {exc}")
        return None


args: argparse.Namespace  # module-level for access in nested functions


def main() -> None:
    global args
    args = _parse_args()

    random.seed(args.seed)

    count_parts = args.counts.split(",")
    if len(count_parts) != 3:
        raise SystemExit("--counts must be three comma-separated integers, e.g. 40,40,20")
    count_a, count_b, count_c = [int(x) for x in count_parts]
    total = count_a + count_b + count_c
    print(
        f"Target: {total} QA pairs  (A={count_a} interaction, B={count_b} patient, C={count_c} mechanism)"
    )

    interactions_path = Path(args.interactions)
    if not interactions_path.exists():
        raise SystemExit(f"File not found: {interactions_path}\nRun prepare_ddi_corpus.py first.")

    interactions: list[dict] = json.loads(interactions_path.read_text(encoding="utf-8"))
    interactions = _prioritize(interactions)
    drugs_dir = Path(args.drugs_dir)

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key and not args.dry_run:
        raise SystemExit("OPENROUTER_API_KEY env var is required (or use --dry-run)")

    client = None
    if not args.dry_run:
        try:
            from openai import OpenAI  # type: ignore[import]
        except ImportError:
            raise SystemExit("Install openai: uv add openai") from None
        client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    all_pairs: list[dict] = []

    # Sample interaction records for each type
    pool_a = interactions[: max(count_a * 3, 50)]
    pool_b = interactions[: max(count_b * 3, 50)]
    pool_c = [r for r in interactions if r["interaction_type"] in ("MECHANISM", "EFFECT")]
    pool_c = pool_c[: max(count_c * 3, 30)] if pool_c else interactions[: max(count_c * 3, 30)]

    random.shuffle(pool_a)
    random.shuffle(pool_b)
    random.shuffle(pool_c)

    def _run_type(label: str, pool: list[dict], target: int, generator) -> list[dict]:
        collected: list[dict] = []
        for record in pool:
            if len(collected) >= target:
                break
            print(
                f"  [{label}] {len(collected) + 1}/{target} — {record['drug1']} + {record['drug2']}",
                end=" ",
            )
            pair = generator(record)
            if pair and pair.get("question") and pair.get("gold_answer"):
                collected.append(pair)
                print("✓")
            else:
                print("—")
        return collected

    print("\n[Type A] Multi-drug interactions…")
    pairs_a = _run_type(
        "A",
        pool_a,
        count_a,
        lambda r: _generate_type_a(client, args.model, r, args.delay, args.dry_run),
    )
    all_pairs.extend(pairs_a)
    output_path.write_text(json.dumps(all_pairs, indent=2, ensure_ascii=False))

    print("\n[Type B] Patient profile scenarios…")
    pairs_b = _run_type(
        "B",
        pool_b,
        count_b,
        lambda r: _generate_type_b(client, args.model, r, drugs_dir, args.delay, args.dry_run),
    )
    all_pairs.extend(pairs_b)
    output_path.write_text(json.dumps(all_pairs, indent=2, ensure_ascii=False))

    print("\n[Type C] Mechanism-focused…")
    pairs_c = _run_type(
        "C",
        pool_c,
        count_c,
        lambda r: _generate_type_c(client, args.model, r, args.delay, args.dry_run),
    )
    all_pairs.extend(pairs_c)
    output_path.write_text(json.dumps(all_pairs, indent=2, ensure_ascii=False))

    print(f"\nDone: {len(all_pairs)}/{total} QA pairs written to {output_path}")
    by_type: dict[str, int] = {}
    for p in all_pairs:
        t = p.get("metadata", {}).get("type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
    print("  By type:", by_type)


if __name__ == "__main__":
    main()
