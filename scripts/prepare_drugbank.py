#!/usr/bin/env python3
"""
Prepare Dataset B: DrugBank open-data CSVs.

Expects two CSV files downloaded from go.drugbank.com/releases/latest#open-data:
  data/raw/drugbank_vocabulary.csv
  data/raw/drug_interactions.csv

Outputs:
  data/drugbank_docs/           — one .txt per drug and per interaction (for ingestion)
  data/drugbank_interactions.json — list of interaction records (input for generate_drugbank_qa.py)

Usage:
    python scripts/prepare_drugbank.py
    python scripts/prepare_drugbank.py --raw-dir /tmp/raw --output-dir /tmp/data
"""

import argparse
import csv
import json
import re
from pathlib import Path


def _slug(text: str, max_len: int = 80) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return s[:max_len]


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Prepare DrugBank dataset for medRAG benchmark")
    p.add_argument(
        "--raw-dir",
        default="data/raw",
        help="Directory containing drugbank CSV files (default: data/raw/)",
    )
    p.add_argument(
        "--output-dir",
        default="data",
        help="Root output directory (default: data/)",
    )
    return p.parse_args()


def _load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_doc(docs_dir: Path, name: str, content: str) -> None:
    fname = _slug(name) + ".txt"
    # Avoid overwriting by appending index if collision
    target = docs_dir / fname
    idx = 1
    while target.exists():
        target = docs_dir / f"{_slug(name)}_{idx}.txt"
        idx += 1
    target.write_text(content, encoding="utf-8")


def main() -> None:
    args = _parse_args()

    raw_dir = Path(args.raw_dir)
    output_dir = Path(args.output_dir)
    docs_dir = output_dir / "drugbank_docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    vocab_path = raw_dir / "drugbank_vocabulary.csv"
    interactions_path = raw_dir / "drug_interactions.csv"

    for p in (vocab_path, interactions_path):
        if not p.exists():
            raise SystemExit(
                f"Missing file: {p}\nDownload from go.drugbank.com/releases/latest#open-data"
            )

    # --- Drug documents ---
    print("Processing drugbank_vocabulary.csv…")
    vocab_rows = _load_csv(vocab_path)
    drug_by_id: dict[str, str] = {}

    for row in vocab_rows:
        drug_id = row.get("DrugBank ID", "").strip()
        name = row.get("Common name", row.get("Name", "")).strip()
        description = row.get("Description", "").strip()
        if not drug_id or not name:
            continue
        drug_by_id[drug_id] = name
        content = f"{name} ({drug_id})\nDescription: {description}\n"
        _write_doc(docs_dir, f"drug_{drug_id}", content)

    print(f"  Drug documents: {len(drug_by_id)}")

    # --- Interaction documents ---
    print("Processing drug_interactions.csv…")
    interaction_rows = _load_csv(interactions_path)
    interactions: list[dict[str, str]] = []

    for row in interaction_rows:
        drug1_id = row.get("DrugBank ID", "").strip()
        drug1_name = row.get("Name", drug_by_id.get(drug1_id, drug1_id)).strip()
        drug2_id = row.get("Interacting Drug ID", row.get("Drug2 DrugBank ID", "")).strip()
        drug2_name = row.get(
            "Interacting Drug Name",
            row.get("Drug2 Name", drug_by_id.get(drug2_id, drug2_id)),
        ).strip()
        description = row.get("Description", "").strip()

        if not drug1_id or not drug2_id or not description:
            continue

        content = f"Interaction: {drug1_name} + {drug2_name}\n{description}\n"
        _write_doc(docs_dir, f"interaction_{drug1_id}_{drug2_id}", content)

        interactions.append(
            {
                "drug1": drug1_name,
                "drug2": drug2_name,
                "drug1_id": drug1_id,
                "drug2_id": drug2_id,
                "description": description,
            }
        )

    interactions_path_out = output_dir / "drugbank_interactions.json"
    interactions_path_out.write_text(
        json.dumps(interactions, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"  Interaction records: {len(interactions)}")
    print("\nOutputs:")
    print(f"  Documents:    {docs_dir}/  ({len(drug_by_id) + len(interactions)} files)")
    print(f"  Interactions: {interactions_path_out}  ({len(interactions)} records)")


if __name__ == "__main__":
    main()
