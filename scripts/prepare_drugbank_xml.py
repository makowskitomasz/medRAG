#!/usr/bin/env python3
"""
Prepare DrugBank interaction data from dhimmel/drugbank XML (GitHub).

Parses drugbank.xml.gz from the dhimmel/drugbank repo (DrugBank data
republished for academic use by Daniel Himmelstein, Rephetio project).

Outputs:
  data/drugbank_xml_docs/interactions/   — one .txt per interaction pair
  data/drugbank_xml_interactions.json    — interaction records for QA generation

Usage:
    python scripts/prepare_drugbank_xml.py
    python scripts/prepare_drugbank_xml.py --output-dir ../data
    python scripts/prepare_drugbank_xml.py --dry-run
"""

import argparse
import gzip
import io
import json
import re
from pathlib import Path
from xml.etree import ElementTree as ET

import httpx

DRUGBANK_XML_URL = (
    "https://raw.githubusercontent.com/dhimmel/drugbank/master/download/drugbank.xml.gz"
)

NS = "http://www.drugbank.ca"


def _slug(text: str, max_len: int = 80) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return s[:max_len]


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Parse DrugBank XML for medRAG benchmark")
    p.add_argument("--output-dir", default="../data", help="Root output dir (default: ../data/)")
    p.add_argument(
        "--xml-cache",
        default="../data/raw/drugbank.xml.gz",
        help="Local cache path for XML (default: ../data/raw/drugbank.xml.gz)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse only first 100 drugs, no network download if cache missing",
    )
    return p.parse_args()


def _download_xml(url: str, cache_path: Path) -> bytes:
    if cache_path.exists():
        print(f"Using cached XML from {cache_path}…")
        return cache_path.read_bytes()

    print("Downloading DrugBank XML from GitHub (~45 MB)…")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with (
        httpx.Client(timeout=120.0, follow_redirects=True) as client,
        client.stream("GET", url) as r,
    ):
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        chunks: list[bytes] = []
        downloaded = 0
        for chunk in r.iter_bytes(chunk_size=1024 * 256):
            chunks.append(chunk)
            downloaded += len(chunk)
            if total:
                pct = downloaded / total * 100
                print(f"\r  {pct:.0f}% ({downloaded // 1024 // 1024} MB)", end="", flush=True)
        print()
    data = b"".join(chunks)
    cache_path.write_bytes(data)
    print(f"  Saved to {cache_path}")
    return data


def _parse_interactions(xml_bytes: bytes, dry_run: bool) -> list[dict]:
    print("Parsing XML…")
    with gzip.open(io.BytesIO(xml_bytes)) as f:
        tree = ET.parse(f)

    root = tree.getroot()
    interactions: list[dict] = []
    seen: set[tuple[str, str]] = set()

    drugs = root.findall(f"{{{NS}}}drug")
    if dry_run:
        drugs = drugs[:100]

    for drug in drugs:
        # Primary drug name and ID
        name_el = drug.find(f"{{{NS}}}name")
        id_el = drug.find(f"{{{NS}}}drugbank-id[@primary='true']")
        if name_el is None or id_el is None:
            continue
        drug1_name = name_el.text or ""
        drug1_id = id_el.text or ""

        ddi_list = drug.find(f"{{{NS}}}drug-interactions")
        if ddi_list is None:
            continue

        for ddi in ddi_list.findall(f"{{{NS}}}drug-interaction"):
            drug2_id_el = ddi.find(f"{{{NS}}}drugbank-id")
            drug2_name_el = ddi.find(f"{{{NS}}}name")
            desc_el = ddi.find(f"{{{NS}}}description")

            drug2_id = drug2_id_el.text if drug2_id_el is not None else ""
            drug2_name = drug2_name_el.text if drug2_name_el is not None else ""
            description = desc_el.text if desc_el is not None else ""

            if not drug1_name or not drug2_name or not description:
                continue
            description = description.strip()
            if not description:
                continue

            # Canonical dedup key (alphabetical order)
            d1, d2 = sorted([drug1_name, drug2_name], key=str.lower)
            key = (_slug(d1), _slug(d2))
            if key in seen:
                continue
            seen.add(key)

            interactions.append(
                {
                    "drug1": d1,
                    "drug2": d2,
                    "drug1_id": drug1_id if d1 == drug1_name else drug2_id,
                    "drug2_id": drug2_id if d2 == drug2_name else drug1_id,
                    "description": description,
                }
            )

    return interactions


def main() -> None:
    args = _parse_args()

    output_dir = Path(args.output_dir)
    interactions_dir = output_dir / "drugbank_xml_docs" / "interactions"
    interactions_dir.mkdir(parents=True, exist_ok=True)

    cache_path = Path(args.xml_cache)

    if args.dry_run and not cache_path.exists():
        raise SystemExit("Dry-run requires cached XML. Run without --dry-run first to download.")

    xml_bytes = _download_xml(DRUGBANK_XML_URL, cache_path)
    interactions = _parse_interactions(xml_bytes, dry_run=args.dry_run)
    print(f"  Unique interaction pairs: {len(interactions)}")

    print("Writing interaction files…")
    for record in interactions:
        slug1 = _slug(record["drug1"])
        slug2 = _slug(record["drug2"])
        fname = f"{slug1}__{slug2}.txt"
        content = (
            f"Drug Interaction: {record['drug1']} + {record['drug2']}\n\n{record['description']}\n"
        )
        (interactions_dir / fname).write_text(content, encoding="utf-8")
        record["doc_file"] = f"drugbank_xml_docs/interactions/{fname}"

    out_json = output_dir / "drugbank_xml_interactions.json"
    out_json.write_text(json.dumps(interactions, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\nOutputs:")
    print(f"  Interaction docs: {interactions_dir}/  ({len(interactions)} files)")
    print(f"  Interactions JSON: {out_json}")


if __name__ == "__main__":
    main()
