#!/usr/bin/env python3
"""
Prepare DDI Corpus (bigbio/ddi_corpus) for medRAG benchmark.

Downloads the DDI Extraction 2013 dataset from HuggingFace and produces:
  data/ddi_docs/interactions/   — one .txt per unique drug-drug interaction
  data/ddi_interactions.json    — interaction records for generate_ddi_qa.py

Usage:
    python scripts/prepare_ddi_corpus.py
    python scripts/prepare_ddi_corpus.py --output-dir /tmp/data --split train+test
"""

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from datasets import load_dataset  # type: ignore[import]

# DDI relation types from the corpus
DDI_TYPES = {"MECHANISM", "EFFECT", "ADVISE", "INT"}


def _slug(text: str, max_len: int = 80) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return s[:max_len]


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Prepare DDI corpus for medRAG benchmark")
    p.add_argument("--output-dir", default="data", help="Root output directory (default: data/)")
    p.add_argument(
        "--split",
        default="train+test",
        help="Dataset splits to use, e.g. train, test, train+test (default: train+test)",
    )
    p.add_argument(
        "--min-text-length",
        type=int,
        default=50,
        help="Minimum passage text length in characters (default: 50)",
    )
    return p.parse_args()


def _load_splits(split_str: str) -> list:
    """Load one or more splits and concatenate."""
    splits = [s.strip() for s in split_str.split("+")]
    rows: list = []
    for split in splits:
        ds = load_dataset(
            "bigbio/ddi_corpus", name="ddi_corpus_bigbio_kb", split=split, trust_remote_code=True
        )
        rows.extend(ds)
        print(f"  Loaded split '{split}': {len(ds)} documents")
    return rows


def _extract_entity_map(doc: dict) -> dict[str, str]:
    """Return {entity_id: normalized_text} for all drug entities in doc."""
    emap: dict[str, str] = {}
    for entity in doc.get("entities", []):
        eid = entity.get("id", "")
        texts = entity.get("text", [])
        if eid and texts:
            emap[eid] = texts[0].strip()
    return emap


def _passage_text(doc: dict) -> str:
    """Concatenate all passage texts for a document."""
    parts: list[str] = []
    for passage in doc.get("passages", []):
        for text_item in passage.get("text", []):
            if isinstance(text_item, str):
                parts.append(text_item.strip())
    return " ".join(parts)


def main() -> None:
    args = _parse_args()

    output_dir = Path(args.output_dir)
    interactions_dir = output_dir / "ddi_docs" / "interactions"
    interactions_dir.mkdir(parents=True, exist_ok=True)

    print("Loading bigbio/ddi_corpus from HuggingFace…")
    rows = _load_splits(args.split)
    print(f"  Total documents: {len(rows)}")

    # Deduplicate interactions by (drug1_slug, drug2_slug) — keep longest description
    seen: dict[tuple[str, str], dict] = {}

    for doc in rows:
        entity_map = _extract_entity_map(doc)
        full_text = _passage_text(doc)

        if len(full_text) < args.min_text_length:
            continue

        for rel in doc.get("relations", []):
            rel_type = rel.get("type", "").upper()
            if rel_type not in DDI_TYPES:
                continue

            arg1_ids = rel.get("arg1_id", "")
            arg2_ids = rel.get("arg2_id", "")

            drug1 = entity_map.get(arg1_ids, "").strip()
            drug2 = entity_map.get(arg2_ids, "").strip()

            if not drug1 or not drug2 or drug1.lower() == drug2.lower():
                continue

            # Canonical order: alphabetical so (A,B) == (B,A)
            d1, d2 = sorted([drug1, drug2], key=str.lower)
            key = (_slug(d1), _slug(d2))

            if key not in seen or len(full_text) > len(seen[key]["source_text"]):
                seen[key] = {
                    "drug1": d1,
                    "drug2": d2,
                    "interaction_type": rel_type,
                    "source_text": full_text,
                }

    print(f"  Unique interaction pairs: {len(seen)}")

    # Write .txt files and collect records
    interactions: list[dict] = []
    for (slug1, slug2), record in seen.items():
        fname = f"{slug1}__{slug2}.txt"
        content = (
            f"Drug Interaction: {record['drug1']} + {record['drug2']}\n"
            f"Interaction Type: {record['interaction_type']}\n\n"
            f"{record['source_text']}\n"
        )
        (interactions_dir / fname).write_text(content, encoding="utf-8")

        interactions.append(
            {
                "drug1": record["drug1"],
                "drug2": record["drug2"],
                "interaction_type": record["interaction_type"],
                "source_text": record["source_text"],
                "doc_file": f"interactions/{fname}",
            }
        )

    interactions.sort(key=lambda r: (r["drug1"].lower(), r["drug2"].lower()))

    out_json = output_dir / "ddi_interactions.json"
    out_json.write_text(json.dumps(interactions, indent=2, ensure_ascii=False), encoding="utf-8")

    # Summary by interaction type
    by_type: dict[str, int] = defaultdict(int)
    for r in interactions:
        by_type[r["interaction_type"]] += 1

    print("\nOutputs:")
    print(f"  Interaction docs:  {interactions_dir}/  ({len(interactions)} files)")
    print(f"  Interactions JSON: {out_json}")
    print("  By type:", dict(sorted(by_type.items())))


if __name__ == "__main__":
    main()
