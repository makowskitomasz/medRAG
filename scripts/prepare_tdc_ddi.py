#!/usr/bin/env python3
"""
Prepare TDC DrugBank DDI dataset for medRAG benchmark.

Uses Therapeutics Data Commons (Harvard) which legally redistributes DrugBank DDI
data as an ML benchmark. Downloads 191 808 drug-drug interaction pairs with
natural-language description templates, then resolves DrugBank IDs to drug names
via PubChem API.

Outputs:
  data/tdc_docs/interactions/   — one .txt per unique interaction type+pair
  data/tdc_interactions.json    — interaction records for generate_ddi_qa.py

Usage:
    python scripts/prepare_tdc_ddi.py
    python scripts/prepare_tdc_ddi.py --output-dir ../data --max-pairs 5000
    python scripts/prepare_tdc_ddi.py --dry-run
"""

import argparse
import json
import re
import time
from pathlib import Path

import httpx
import pandas as pd

PUBCHEM_API = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
PUBCHEM_DELAY = 0.22  # ~4.5 req/s, safely under 5/s limit


def _slug(text: str, max_len: int = 80) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return s[:max_len]


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Prepare TDC DrugBank DDI for medRAG")
    p.add_argument("--output-dir", default="../data", help="Root output dir (default: ../data/)")
    p.add_argument(
        "--tdc-cache",
        default="./data/drugbank.tab",
        help="Path to TDC cached tab file (default: ./data/drugbank.tab)",
    )
    p.add_argument(
        "--max-pairs",
        type=int,
        default=None,
        help="Limit number of pairs to process (default: all ~191K)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Download data but skip PubChem lookups; use DrugBank IDs as names",
    )
    return p.parse_args()


def _load_tab(path: Path) -> pd.DataFrame:
    """Load TDC drugbank.tab — fallback to PyTDC download if missing."""
    if path.exists():
        print(f"Loading cached TDC data from {path}…")
        df = pd.read_csv(path, sep="\t")
    else:
        print("Downloading TDC DrugBank DDI via PyTDC…")
        try:
            from tdc.multi_pred import DDI  # type: ignore[import]
        except ImportError:
            raise SystemExit("Install PyTDC: uv add PyTDC") from None
        DDI(name="DrugBank")
        # Raw tab file is written to ./data/ by TDC
        raw = Path("./data/drugbank.tab")
        if raw.exists():
            df = pd.read_csv(raw, sep="\t")
        else:
            raise SystemExit(f"TDC tab file not found at {raw}")
    required = {"ID1", "ID2", "Map"}
    if not required.issubset(df.columns):
        raise SystemExit(f"Expected columns {required}, got {set(df.columns)}")
    return df


def _resolve_drug_names(
    drug_ids: list[str],
    dry_run: bool,
) -> dict[str, str]:
    """Map DrugBank IDs → drug names via PubChem xref API."""
    if dry_run:
        return {did: did for did in drug_ids}

    names: dict[str, str] = {}
    total = len(drug_ids)
    print(f"Resolving {total} DrugBank IDs via PubChem…")

    with httpx.Client(timeout=10.0) as client:
        for i, did in enumerate(drug_ids, 1):
            if i % 100 == 0:
                print(f"  [{i}/{total}] resolved so far: {len(names)}")
            url = f"{PUBCHEM_API}/compound/xref/RegistryID/{did}/property/Title/JSON"
            try:
                r = client.get(url)
                if r.status_code == 200:
                    props = r.json().get("PropertyTable", {}).get("Properties", [])
                    if props:
                        names[did] = props[0].get("Title", did)
                    else:
                        names[did] = did
                else:
                    names[did] = did
            except Exception:
                names[did] = did
            time.sleep(PUBCHEM_DELAY)

    found = sum(1 for k, v in names.items() if v != k)
    print(f"  Resolved {found}/{total} IDs to drug names")
    return names


def _fill_template(template: str, name1: str, name2: str) -> str:
    return template.replace("#Drug1", name1).replace("#Drug2", name2)


def main() -> None:
    args = _parse_args()

    output_dir = Path(args.output_dir)
    interactions_dir = output_dir / "tdc_docs" / "interactions"
    interactions_dir.mkdir(parents=True, exist_ok=True)

    df = _load_tab(Path(args.tdc_cache))
    print(f"  Total pairs: {len(df)}")

    if args.max_pairs:
        df = df.head(args.max_pairs)
        print(f"  Limiting to {args.max_pairs} pairs")

    # Collect unique DrugBank IDs
    all_ids = list(set(df["ID1"].tolist() + df["ID2"].tolist()))
    id_to_name = _resolve_drug_names(all_ids, dry_run=args.dry_run)

    # Deduplicate by (slug1, slug2, interaction_type)
    seen: set[tuple[str, str, str]] = set()
    interactions: list[dict] = []
    skipped = 0

    print("Writing interaction files…")
    for _, row in df.iterrows():
        id1: str = str(row["ID1"])
        id2: str = str(row["ID2"])
        template: str = str(row.get("Map", ""))
        y_val: str = str(row.get("Y", ""))

        name1 = id_to_name.get(id1, id1)
        name2 = id_to_name.get(id2, id2)

        description = _fill_template(template, name1, name2) if template else ""
        if not description:
            skipped += 1
            continue

        # Canonical order so A+B == B+A only when description is symmetric;
        # keep original order to preserve direction in description
        slug1 = _slug(name1)
        slug2 = _slug(name2)
        key = (slug1, slug2, y_val)

        if key in seen:
            continue
        seen.add(key)

        fname = f"{slug1}__{slug2}.txt"
        # Avoid collisions from same name pair with different interaction types
        target = interactions_dir / fname
        if target.exists():
            base = f"{slug1}__{slug2}_{y_val}"
            target = interactions_dir / f"{base}.txt"

        content = (
            f"Drug Interaction: {name1} + {name2}\nInteraction Type: {y_val}\n\n{description}\n"
        )
        target.write_text(content, encoding="utf-8")

        interactions.append(
            {
                "drug1": name1,
                "drug2": name2,
                "drug1_id": id1,
                "drug2_id": id2,
                "interaction_type": y_val,
                "description": description,
                "doc_file": f"tdc_docs/interactions/{target.name}",
            }
        )

    out_json = output_dir / "tdc_interactions.json"
    out_json.write_text(json.dumps(interactions, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\nOutputs:")
    print(f"  Interaction docs: {interactions_dir}/  ({len(interactions)} files)")
    print(f"  Interactions JSON: {out_json}")
    print(f"  Skipped (no description): {skipped}")


if __name__ == "__main__":
    main()
