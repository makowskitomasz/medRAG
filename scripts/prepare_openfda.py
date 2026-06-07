#!/usr/bin/env python3
"""
Prepare drug profiles from OpenFDA drug labels for medRAG benchmark.

Reads drug names from data/ddi_interactions.json, queries the OpenFDA API
for each drug, and writes one .txt profile per drug to data/ddi_docs/drugs/.

OpenFDA drug label sections extracted:
  - drug_interactions
  - warnings_and_cautions / boxed_warnings
  - contraindications
  - indications_and_usage

No API key required. Rate limit: 240 req/min (unauthenticated).

Usage:
    python scripts/prepare_openfda.py
    python scripts/prepare_openfda.py --interactions data/ddi_interactions.json --delay 0.3
    python scripts/prepare_openfda.py --dry-run
"""

import argparse
import json
import re
import time
from pathlib import Path

import httpx

OPENFDA_BASE = "https://api.fda.gov/drug/label.json"

LABEL_FIELDS = [
    "drug_interactions",
    "warnings_and_cautions",
    "boxed_warnings",
    "contraindications",
    "indications_and_usage",
    "mechanism_of_action",
]


def _slug(text: str, max_len: int = 80) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return s[:max_len]


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Download OpenFDA drug profiles for medRAG")
    p.add_argument(
        "--interactions",
        default="../data/ddi_interactions.json",
        help="Path to ddi_interactions.json (default: ../data/ddi_interactions.json)",
    )
    p.add_argument(
        "--output-dir",
        default="../data",
        help="Root output directory (default: ../data/)",
    )
    p.add_argument(
        "--delay",
        type=float,
        default=0.25,
        help="Seconds between API calls (default: 0.25 → ~240 req/min)",
    )
    p.add_argument(
        "--max-drugs",
        type=int,
        default=None,
        help="Limit number of drugs to query (for testing)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print drug list without calling the API",
    )
    return p.parse_args()


def _collect_drug_names(interactions: list[dict]) -> list[str]:
    """Deduplicated, sorted list of all drug names from interaction records."""
    names: set[str] = set()
    for rec in interactions:
        names.add(rec["drug1"].strip())
        names.add(rec["drug2"].strip())
    return sorted(names, key=str.lower)


def _query_openfda(client: httpx.Client, drug_name: str) -> dict | None:
    """Query OpenFDA for a drug by generic name. Returns first result or None."""
    params = {
        "search": f'openfda.generic_name:"{drug_name.upper()}"',
        "limit": "1",
    }
    try:
        r = client.get(OPENFDA_BASE, params=params, timeout=10.0)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        data = r.json()
        results = data.get("results", [])
        return results[0] if results else None
    except Exception:
        return None


def _build_profile(drug_name: str, label: dict) -> str:
    """Convert an OpenFDA label record into a readable text profile."""
    openfda = label.get("openfda", {})
    brand_names = openfda.get("brand_name", [])
    generic_names = openfda.get("generic_name", [])

    lines: list[str] = [
        f"Drug: {drug_name}",
    ]
    if generic_names:
        lines.append(f"Generic Name: {', '.join(generic_names[:3])}")
    if brand_names:
        lines.append(f"Brand Names: {', '.join(brand_names[:5])}")
    lines.append("")

    section_titles = {
        "indications_and_usage": "Indications and Usage",
        "mechanism_of_action": "Mechanism of Action",
        "contraindications": "Contraindications",
        "warnings_and_cautions": "Warnings and Cautions",
        "boxed_warnings": "Boxed Warnings",
        "drug_interactions": "Drug Interactions",
    }

    for field, title in section_titles.items():
        values = label.get(field, [])
        if not values:
            continue
        text = " ".join(values).strip()
        if text:
            lines.append(f"== {title} ==")
            lines.append(text)
            lines.append("")

    return "\n".join(lines)


def main() -> None:
    args = _parse_args()

    interactions_path = Path(args.interactions)
    if not interactions_path.exists():
        raise SystemExit(
            f"Interactions file not found: {interactions_path}\nRun prepare_ddi_corpus.py first."
        )

    interactions: list[dict] = json.loads(interactions_path.read_text(encoding="utf-8"))
    drugs = _collect_drug_names(interactions)

    if args.max_drugs:
        drugs = drugs[: args.max_drugs]

    print(f"Unique drugs to query: {len(drugs)}")

    if args.dry_run:
        print("[dry-run] Drug list (first 20):")
        for d in drugs[:20]:
            print(f"  {d}")
        if len(drugs) > 20:
            print(f"  … and {len(drugs) - 20} more")
        return

    drugs_dir = Path(args.output_dir) / "ddi_docs" / "drugs"
    drugs_dir.mkdir(parents=True, exist_ok=True)

    found = 0
    not_found = 0

    with httpx.Client() as client:
        for i, drug in enumerate(drugs, 1):
            slug = _slug(drug)
            out_path = drugs_dir / f"{slug}.txt"

            if out_path.exists():
                print(f"  [{i}/{len(drugs)}] {drug[:40]:<40} (cached)")
                found += 1
                continue

            label = _query_openfda(client, drug)
            if label:
                profile = _build_profile(drug, label)
                out_path.write_text(profile, encoding="utf-8")
                found += 1
                print(f"  [{i}/{len(drugs)}] {drug[:40]:<40} ✓")
            else:
                not_found += 1
                print(f"  [{i}/{len(drugs)}] {drug[:40]:<40} — not found")

            if args.delay > 0:
                time.sleep(args.delay)

    print(f"\nDone: {found} profiles saved, {not_found} not found")
    print(f"Output: {drugs_dir}/")


if __name__ == "__main__":
    main()
