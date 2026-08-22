#!/usr/bin/env python3
"""
Generate a 5-level DDI benchmark (100 QA pairs) using OpenRouter API.

Each question is grounded in N source files fed as context; the answer
requires synthesising information from ALL of them.

Level  Files  Source mix                              Focus
  1      1    drug profile (OpenFDA)                  patient "can I take X?"
  2      2    2 drug profiles                         clinical, dual-drug profile
  3      3    2 profiles + 1 interaction              multi-hop, 3-entity reasoning
  4      6    4 profiles + 2 interactions             full patient case w/ comorbidities
  5      7    4 profiles + 3 interactions             expert PK/PD mechanisms & synthesis

Reads:
  data/ddi_docs/drugs/            — OpenFDA drug profiles (.txt)
  data/ddi_docs/interactions/     — DDI interaction pairs (.txt)
  data/drugbank_xml_docs/interactions/ — DrugBank interaction pairs (.txt)

Writes:
  data/ddi_benchmark.json         — 100 QA pairs in RAGAS-ready format

Output record schema:
  {
    "question":      str,
    "ground_truth":  str,
    "contexts":      [str, ...],   # contents of source files
    "level":         int,          # 1–5
    "source_files":  [str, ...],   # file paths relative to data/
    "metadata": {
      "difficulty":   str,
      "focus":        str,
      "drugs":        [str, ...]
    }
  }

Usage:
    python scripts/generate_ddi_benchmark.py --dry-run
    python scripts/generate_ddi_benchmark.py
    python scripts/generate_ddi_benchmark.py --model gpt-4.1-nano --per-level 5

Required env var:
    OPENROUTER_API_KEY
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import threading
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# ---------------------------------------------------------------------------
# System prompts per level
# ---------------------------------------------------------------------------

_LEVEL_META = {
    1: {
        "difficulty": "Easy",
        "focus": "patient question about a single drug (indications, contraindications, warnings)",
        "instruction": (
            "Write a realistic question a PATIENT would ask their pharmacist or doctor — "
            "e.g. 'Can I take this drug if I have condition X?', 'What should I avoid while on this?', "
            "'Is this safe during pregnancy?', 'What warning signs should I watch for?'. "
            "Use plain language, first-person or second-person voice. "
            "The answer must be grounded exclusively in the provided document — "
            "do NOT mention any drug, condition, or fact not present in the text."
        ),
    },
    2: {
        "difficulty": "Medium",
        "focus": "clinical question about the direct interaction between the two drugs",
        "instruction": (
            "You are given TWO drug profiles AND one interaction record between them. "
            "Write a clinical question about what happens when these two specific drugs are used "
            "together — e.g. what risk arises, what monitoring is needed, or what mechanism "
            "explains the interaction. "
            "The answer MUST cite: (a) the interaction mechanism or risk from the interaction "
            "record, (b) a pharmacological property from Drug A's profile that explains WHY the "
            "interaction occurs, AND (c) a clinical consequence or monitoring parameter from "
            "Drug B's profile. Removing any one of the three documents makes the answer incomplete. "
            "Do NOT introduce any drug, enzyme, condition, or fact not present in the documents."
        ),
    },
    3: {
        "difficulty": "Hard",
        "focus": "multi-hop reasoning across 3 entities (2 profiles + 1 interaction record)",
        "instruction": (
            "Write a multi-hop question that chains facts across ALL THREE documents. "
            "The chain must be: a specific mechanism or risk stated in the interaction record "
            "(Document 3) that can only be fully explained by combining pharmacological details "
            "from both drug profiles (Documents 1 and 2). "
            "Example chain: 'interaction record says Drug A increases Drug B exposure → "
            "Drug A profile explains it inhibits CYP3A4 → Drug B profile shows it is a CYP3A4 "
            "substrate with a narrow therapeutic index → therefore monitor for toxicity'. "
            "The answer must explicitly use a fact from each of the three documents. "
            "Do NOT introduce any drug, enzyme, condition, or fact not present in the documents."
        ),
    },
    4: {
        "difficulty": "Very Hard",
        "focus": "full patient case with comorbidities, polypharmacy, multiple interactions",
        "instruction": (
            "Write a patient-case question describing a realistic patient (age, sex, 2+ "
            "comorbidities) whose drug regimen consists EXACTLY of the four drugs in the profiles "
            "provided — no other drugs. Ask whether the complete combination is safe or how to "
            "manage conflicts. "
            "The answer must reference a specific finding from EACH of the six documents: "
            "for each drug profile cite the relevant contraindication, warning, or PK property; "
            "for each interaction record cite the specific risk or mechanism stated. "
            "STRICT RULE: do not mention any drug, condition, enzyme, or clinical fact that does "
            "not appear verbatim or by clear implication in the provided texts."
        ),
    },
    5: {
        "difficulty": "Expert",
        "focus": "pharmacological mechanisms, PK/PD synthesis across 4 drugs and 3 interaction records",
        "instruction": (
            "Write one expert mechanistic question using ALL SEVEN documents. "
            "The question must link at least two interaction records through a shared mechanism "
            "and reference drug profile properties that explain why. "
            "The answer must cite one specific fact from each document. "
            "Do not introduce any drug, enzyme, or fact absent from the texts."
        ),
    },
}

_SYSTEM_PROMPT = """\
You are a clinical pharmacology expert creating a benchmark dataset.
Given one or more drug reference documents, produce ONE QA pair.

ABSOLUTE RULES — violating any of these makes the pair unusable:
1. DOCUMENT-ONLY FACTS: Every fact in both the question and the answer must come from the
   provided documents. Do not use your training knowledge to add drugs, enzymes, conditions,
   mechanisms, or monitoring parameters that are not explicitly stated in the texts.
2. CROSS-DOCUMENT SYNTHESIS: The question must be unanswerable from any single document alone —
   the answer must visibly draw on information from EACH document provided.
3. OUTPUT FORMAT: Return ONLY a JSON object with exactly two keys: "question" and "ground_truth".
   No markdown fences, no commentary, no extra keys.
4. QUESTION: one clear, clinically realistic question (1–3 sentences).
5. GROUND TRUTH: 3–6 sentences. For each key claim, name the document it came from using the
   pattern "per [Drug Name] profile" or "per the [DrugA]–[DrugB] interaction record".
   This citation pattern is mandatory — it makes the cross-document grounding verifiable.
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def _drug_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:80]


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _run_heartbeat(stop: threading.Event) -> None:
    while not stop.wait(3):
        print(".", end="", flush=True)


def _call_llm(client, model: str, context: str, instruction: str, retries: int = 3) -> dict:
    user_msg = f"{instruction}\n\n{'=' * 60}\n{context}"
    last_exc: Exception = RuntimeError("no attempts made")
    for attempt in range(1, retries + 1):
        raw_chunks: list[str] = []

        # heartbeat thread — prints a dot every 3s so the user knows the model is thinking
        _stop_heartbeat = threading.Event()
        hb = threading.Thread(target=_run_heartbeat, args=(_stop_heartbeat,), daemon=True)
        hb.start()

        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.7,
                max_tokens=16384,
                timeout=300,
            )
            content = resp.choices[0].message.content if resp.choices else None
            if content:
                raw_chunks.append(content)
        except Exception as exc:
            last_exc = exc
            print(f"\n    [retry {attempt}/{retries}] API error: {exc}", end=" ")
            time.sleep(2)
            continue
        finally:
            _stop_heartbeat.set()

        raw = "".join(raw_chunks)
        if not raw.strip():
            reason = resp.choices[0].finish_reason if resp.choices else "unknown"
            usage = getattr(resp, "usage", None)
            reasoning_tokens = getattr(
                getattr(usage, "completion_tokens_details", None), "reasoning_tokens", "?"
            )
            last_exc = ValueError(
                f"Empty response (finish_reason={reason}, reasoning_tokens={reasoning_tokens})"
            )
            print(f"\n    [retry {attempt}/{retries}] {last_exc}", end=" ")
            time.sleep(1)
            continue
        try:
            parsed = json.loads(_strip_fences(raw))
            if isinstance(parsed.get("ground_truth"), list):
                parsed["ground_truth"] = " ".join(parsed["ground_truth"])
            return parsed
        except json.JSONDecodeError:
            preview = raw[:400].replace("\n", " ")
            last_exc = ValueError(f"Bad JSON — got: {preview!r}")
            print(f"\n    [retry {attempt}/{retries}] {last_exc}", end=" ")
            time.sleep(1)
    raise last_exc


def _dummy_pair(drugs: list[str], level: int) -> dict:
    return {
        "question": f"[DRY-RUN L{level}] What is the clinical significance of combining "
        + " + ".join(drugs)
        + "?",
        "ground_truth": "[DRY-RUN] This is a placeholder answer.",
    }


# ---------------------------------------------------------------------------
# File pools
# ---------------------------------------------------------------------------


def _build_pools(
    drugs_dir: Path,
    ddi_interactions_dir: Path,
    drugbank_interactions_dir: Path,
    priority_drugs: set[str],
    drugbank_ratio: float = 0.75,
) -> tuple[list[Path], list[Path]]:
    """Return (drug_profiles, interactions) where interactions are 75% DrugBank / 25% DDI."""

    def _sort_key(p: Path) -> int:
        return 0 if any(d in p.stem for d in priority_drugs) else 1

    drugs = sorted(
        (p for p in drugs_dir.glob("*.txt") if p.stem not in _PROFILE_BLACKLIST),
        key=_sort_key,
    )
    ddi = [
        p
        for p in ddi_interactions_dir.glob("*.txt")
        if not any(b in p.stem for b in _PROFILE_BLACKLIST)
    ]
    db = [
        p
        for p in drugbank_interactions_dir.glob("*.txt")
        if not any(b in p.stem for b in _PROFILE_BLACKLIST)
    ]

    # build a 75/25 interleaved list: for every 3 DrugBank pick 1 DDI
    random.shuffle(ddi)
    random.shuffle(db)
    n_total = len(ddi) + len(db)
    n_db = int(n_total * drugbank_ratio)
    n_ddi = n_total - n_db
    mixed = db[:n_db] + ddi[:n_ddi]
    random.shuffle(mixed)

    return drugs, mixed


def _drug_names_from_profile(path: Path) -> list[str]:
    """Extract drug name from profile filename."""
    return [path.stem.replace("_", " ").title()]


def _drug_names_from_interaction(path: Path) -> list[str]:
    parts = path.stem.split("__")
    return [p.replace("_", " ").title() for p in parts]


# ---------------------------------------------------------------------------
# Samplers per level
# ---------------------------------------------------------------------------


def _sample_level1(
    drug_profiles: list[Path], used: set[str]
) -> tuple[list[Path], list[str]] | None:
    for p in drug_profiles:
        if p.stem not in used:
            used.add(p.stem)
            return [p], _drug_names_from_profile(p)
    return None


def _sample_level2(
    drug_profiles: list[Path],
    interactions: list[Path],
    used: set[str],
) -> tuple[list[Path], list[str]] | None:
    # pick an interaction record, then return both profiles + the interaction file
    profile_pool = {p.stem: p for p in drug_profiles}
    for ix in interactions:
        if ix.stem in used:
            continue
        d1, d2 = (ix.stem.split("__") + [""])[:2]
        p1 = profile_pool.get(d1)
        p2 = profile_pool.get(d2)
        if not p1 or not p2 or p1.stem in used or p2.stem in used:
            continue
        used.update({ix.stem, p1.stem, p2.stem})
        drugs = [d1.replace("_", " ").title(), d2.replace("_", " ").title()]
        return [p1, p2, ix], drugs
    return None


def _sample_level3(
    drug_profiles: list[Path],
    interactions: list[Path],
    used: set[str],
) -> tuple[list[Path], list[str]] | None:
    profile_pool = {p.stem: p for p in drug_profiles}

    for ix in interactions:
        key = ix.stem
        if key in used:
            continue
        d1, d2 = (ix.stem.split("__") + [""])[:2]
        p1 = profile_pool.get(d1)
        p2 = profile_pool.get(d2)
        if not p1 or not p2 or p1.stem in used or p2.stem in used:
            continue
        used.update({key, p1.stem, p2.stem})
        drugs = [d1.replace("_", " ").title(), d2.replace("_", " ").title()]
        return [p1, p2, ix], drugs
    return None


def _find_extra_profiles(
    profile_pool: dict[str, Path],
    exclude: set[str],
    used: set[str],
    n: int,
) -> list[Path] | None:
    """Return n unused profiles not in exclude."""
    result: list[Path] = []
    for stem, p in profile_pool.items():
        if stem not in exclude and stem not in used:
            result.append(p)
            if len(result) == n:
                return result
    return None if len(result) < n else result


def _sample_level4(
    drug_profiles: list[Path],
    interactions: list[Path],
    used: set[str],
) -> tuple[list[Path], list[str]] | None:
    # 4 profiles + 2 interactions = 6 files
    all_ix = interactions
    profile_pool = {p.stem: p for p in drug_profiles}

    for i, ix1 in enumerate(all_ix):
        if ix1.stem in used:
            continue
        d1a, d1b = (ix1.stem.split("__") + [""])[:2]
        p1a = profile_pool.get(d1a)
        p1b = profile_pool.get(d1b)
        if not p1a or not p1b or p1a.stem in used or p1b.stem in used:
            continue

        for ix2 in all_ix[i + 1 :]:
            if ix2.stem in used:
                continue
            d2a, d2b = (ix2.stem.split("__") + [""])[:2]
            p2a = profile_pool.get(d2a)
            p2b = profile_pool.get(d2b)
            if not p2a or not p2b:
                continue
            known = {d1a, d1b, d2a, d2b}
            profiles_so_far = {p for p in [p1a, p1b, p2a, p2b] if p.stem not in used}
            if len(profiles_so_far) < 4:
                continue
            # pick exactly 4 distinct profiles from the four drug slugs
            unique_profiles: dict[str, Path] = {}
            for slug in (d1a, d1b, d2a, d2b):
                pp = profile_pool.get(slug)
                if pp and pp.stem not in used:
                    unique_profiles[slug] = pp
            if len(unique_profiles) < 4:
                # need a 4th profile from outside
                extras = _find_extra_profiles(profile_pool, known, used, 4 - len(unique_profiles))
                if not extras:
                    continue
                for ep in extras:
                    unique_profiles[ep.stem] = ep
            four_profiles = list(unique_profiles.values())[:4]
            stems = {ix1.stem, ix2.stem} | {p.stem for p in four_profiles}
            if stems & used:
                continue
            used.update(stems)
            drugs = [p.stem.replace("_", " ").title() for p in four_profiles]
            return [*four_profiles, ix1, ix2], drugs
    return None


def _sample_level5(
    drug_profiles: list[Path],
    interactions: list[Path],
    used: set[str],
) -> tuple[list[Path], list[str]] | None:
    # 4 profiles + 3 interactions = 7 files
    all_ix = interactions
    profile_pool = {p.stem: p for p in drug_profiles}

    for i, ix1 in enumerate(all_ix):
        if ix1.stem in used:
            continue
        d1a, d1b = (ix1.stem.split("__") + [""])[:2]
        p1a = profile_pool.get(d1a)
        p1b = profile_pool.get(d1b)
        if not p1a or not p1b or p1a.stem in used or p1b.stem in used:
            continue

        for j, ix2 in enumerate(all_ix[i + 1 :], i + 1):
            if ix2.stem in used:
                continue
            d2a, d2b = (ix2.stem.split("__") + [""])[:2]
            shared12 = {d1a, d1b} & {d2a, d2b}
            if not shared12:
                continue
            p2a = profile_pool.get(d2a)
            p2b = profile_pool.get(d2b)
            if not p2a or not p2b:
                continue

            for ix3 in all_ix[j + 1 :]:
                if ix3.stem in used:
                    continue
                d3a, d3b = (ix3.stem.split("__") + [""])[:2]
                # ix3 must share a drug with ix1 or ix2
                known = {d1a, d1b, d2a, d2b}
                if not ({d3a, d3b} & known):
                    continue
                p3a = profile_pool.get(d3a)
                p3b = profile_pool.get(d3b)
                if not p3a or not p3b:
                    continue

                all_drug_slugs = {d1a, d1b, d2a, d2b, d3a, d3b}
                unique_profiles: dict[str, Path] = {}
                for slug in all_drug_slugs:
                    pp = profile_pool.get(slug)
                    if pp and pp.stem not in used:
                        unique_profiles[slug] = pp

                if len(unique_profiles) < 4:
                    extras = _find_extra_profiles(
                        profile_pool, all_drug_slugs, used, 4 - len(unique_profiles)
                    )
                    if not extras:
                        continue
                    for ep in extras:
                        unique_profiles[ep.stem] = ep

                four_profiles = list(unique_profiles.values())[:4]
                stems = {ix1.stem, ix2.stem, ix3.stem} | {p.stem for p in four_profiles}
                if stems & used:
                    continue
                used.update(stems)
                drugs = [p.stem.replace("_", " ").title() for p in four_profiles]
                return [*four_profiles, ix1, ix2, ix3], drugs
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

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
    "amlodipine",
    "methotrexate",
    "lithium",
    "phenytoin",
    "rifampin",
    "ketoconazole",
    "clarithromycin",
}

# Profiles that are non-drug substances or first-aid agents — unsuitable for clinical QA
_PROFILE_BLACKLIST = {
    "alcohol",  # isopropyl alcohol (first aid), not ethanol
    "acellular",  # vaccine component
    "acetaldehyde",  # metabolite, not a drug
    "acetylcholine_chloride",  # surgical irrigant only
    "cobalt",  # trace element
    "iron",  # ambiguous (supplement vs. compound)
    "ethyl_alcohol",  # same issue as alcohol
    "erythromycin",  # topical 2% only — not oral antibiotic
    "anticoagulant",  # generic aggregate file, not a specific drug
    # duplicates — same drug, different salt/formulation already covered
    "fluoxetine_hydrochloride",  # same as fluoxetine
    "lithium_carbonate",  # same as lithium
    "warfarin_sodium",  # same as warfarin
    "desipramine_hydrochloride",  # same as desipramine
    "sildenafil_citrate",  # same as sildenafil
    # generic categories / non-drug substances
    "diuretic",  # generic category
    "salicylate",  # generic category
    "laxative",  # generic category
    "anticoagulant_citrate_dextrose",  # blood bank reagent
    "tubocurarine",  # obsolete
    # cosmetics / supplements / food additives
    "niacinamide",  # cosmetic ingredient
    "pectin",  # cough drops / food additive
    "sodium_citrate",  # blood bank / food additive
    "l_arginine",  # nutritional supplement
    # ophthalmic-only agents with no systemic profile
    "apraclonidine",  # ophthalmic only
    "fludrocortisone_acetate",  # peripheral, rarely interacts
    # non-drug substances found in OpenFDA profiles by mistake
    "boric_acid",  # topical antiseptic / cleaning agent
    "endotoxin",  # bacterial toxin / OTC cold remedy product
    "paba",  # para-aminobenzoic acid — sunscreen ingredient
    "aluminum",  # antiperspirant, not a systemic drug
    "nicotinic_acid",  # vitamin B3 supplement (not Niaspan)
    "coumarin",  # OTC hay fever product, not anticoagulant warfarin
    "kaolin",  # cosmetic facial clay mask (Derladie Vegan Pink Clay Mask)
    "zinc",  # diaper rash cream (Attitude Diaper Cream), not systemic zinc
    "ethanol",  # lavender hand sanitizer wipes, not pharmaceutical ethanol
    "neomycin",  # OTC triple antibiotic first-aid cream (bacitracin/neomycin/polymyxin)
    "penciclovir",  # topical cold sore cream (Denavir 1%), not systemic antiviral
    "nitrite",  # homeopathic amyl nitrite hot-flash product (Amyl nitrosum)
    "narcotics",  # homeopathic "CESIUM, NARCOTICS, AND DIOXIN DETOX" / Cell Detox
    # GUNA-GERIATRICS homeopathic — same multi-ingredient product mislabelled as multiple drugs
    "melatonin",  # GUNA-GERIATRICS homeopathic (barium carbonate, pork liver, etc.)
    "corticotropin",  # GUNA-GERIATRICS homeopathic
    "oxytocin",  # GUNA-GERIATRICS homeopathic
}


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate 5-level DDI benchmark (100 QA pairs)")
    _root = Path(__file__).parent.parent / "data"
    p.add_argument("--drugs-dir", default=str(_root / "ddi_docs/drugs"))
    p.add_argument("--ddi-interactions-dir", default=str(_root / "ddi_docs/interactions"))
    p.add_argument(
        "--drugbank-interactions-dir", default=str(_root / "drugbank_xml_docs/interactions")
    )
    p.add_argument("--output", default=str(_root / "ddi_benchmark.json"))
    p.add_argument(
        "--model", default="openai/gpt-5-nano", help="OpenRouter model (default: openai/gpt-5-nano)"
    )
    p.add_argument("--per-level", type=int, default=20, help="Questions per level (default: 20)")
    p.add_argument("--delay", type=float, default=0.3, help="Seconds between API calls")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--dry-run", action="store_true", help="Skip API calls, write dummy pairs")
    p.add_argument(
        "--max-chars",
        type=int,
        default=0,
        help="Max chars per source file (0 = auto per level)",
    )
    return p.parse_args()


# chars per file per level — fewer files get more context; L4/L5 capped low to limit reasoning time
_MAX_CHARS_PER_LEVEL = {1: 1500, 2: 1000, 3: 900, 4: 400, 5: 200}


def _build_context(files: list[Path], max_chars: int) -> str:
    parts: list[str] = []
    for i, f in enumerate(files, 1):
        content = _load_text(f)[:max_chars]
        parts.append(f"[Document {i}: {f.name}]\n{content}")
    return "\n\n" + "─" * 60 + "\n\n".join(parts)


def main() -> None:
    args = _parse_args()
    random.seed(args.seed)

    drugs_dir = Path(args.drugs_dir)
    ddi_dir = Path(args.ddi_interactions_dir)
    db_dir = Path(args.drugbank_interactions_dir)
    output_path = Path(args.output)

    for d in (drugs_dir, ddi_dir, db_dir):
        if not d.exists():
            raise SystemExit(f"Directory not found: {d}")

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

    drug_profiles, interactions = _build_pools(drugs_dir, ddi_dir, db_dir, _PRIORITY_DRUGS)

    print(
        f"Pools — drug profiles: {len(drug_profiles)}, "
        f"interactions: {len(interactions)} (75% DrugBank / 25% DDI)"
    )
    print(f"Generating {args.per_level} × 5 levels = {args.per_level * 5} QA pairs…\n")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # resume from checkpoint if file exists
    all_pairs: list[dict] = []
    used: set[str] = set()
    done_per_level: dict[int, int] = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    if output_path.exists():
        try:
            all_pairs = json.loads(output_path.read_text(encoding="utf-8"))
            for pair in all_pairs:
                lv = pair.get("level", 0)
                done_per_level[lv] = done_per_level.get(lv, 0) + 1
                for f in pair.get("source_files", []):
                    used.add(Path(f).stem)
            total_done = sum(done_per_level.values())
            print(f"Resuming from checkpoint: {total_done} pairs already done {done_per_level}\n")
        except Exception:
            print("Checkpoint unreadable — starting fresh.\n")
            all_pairs = []
            used = set()
            done_per_level = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

    samplers = {
        1: lambda: _sample_level1(drug_profiles, used),
        2: lambda: _sample_level2(drug_profiles, interactions, used),
        3: lambda: _sample_level3(drug_profiles, interactions, used),
        4: lambda: _sample_level4(drug_profiles, interactions, used),
        5: lambda: _sample_level5(drug_profiles, interactions, used),
    }

    for level in range(1, 6):
        meta = _LEVEL_META[level]
        already = done_per_level.get(level, 0)
        remaining = args.per_level - already
        if remaining <= 0:
            print(
                f"[Level {level} — {meta['difficulty']}] already complete ({already}/{args.per_level}), skipping."
            )
            continue
        print(f"[Level {level} — {meta['difficulty']}] ({already} done, need {remaining} more)")
        generated = 0
        attempts = 0

        while generated < remaining and attempts < remaining * 10:
            attempts += 1
            sample = samplers[level]()
            if sample is None:
                print(f"  ! Exhausted candidates at level {level}")
                break
            files, drug_names = sample

            print(
                f"  {already + generated + 1}/{args.per_level} — {' + '.join(drug_names[:3])}"
                + (" …" if len(drug_names) > 3 else ""),
                end=" ",
            )

            if args.dry_run:
                pair = _dummy_pair(drug_names, level)
                contexts = [_load_text(f)[:200] for f in files]
            else:
                max_chars = args.max_chars if args.max_chars > 0 else _MAX_CHARS_PER_LEVEL[level]
                context_text = _build_context(files, max_chars)
                try:
                    pair = _call_llm(client, args.model, context_text, meta["instruction"])
                    contexts = [_load_text(f) for f in files]
                    if args.delay > 0:
                        time.sleep(args.delay)
                except Exception as exc:
                    print(f"✗ ({exc})")
                    continue

            if not pair.get("question") or not pair.get("ground_truth"):
                print("✗ (missing keys)")
                continue

            record: dict = {
                "question": pair["question"],
                "ground_truth": pair["ground_truth"],
                "contexts": contexts,
                "level": level,
                "source_files": [str(f) for f in files],
                "metadata": {
                    "difficulty": meta["difficulty"],
                    "focus": meta["focus"],
                    "drugs": drug_names,
                },
            }
            all_pairs.append(record)
            output_path.write_text(json.dumps(all_pairs, indent=2, ensure_ascii=False))
            generated += 1
            print("✓")

        print(
            f"  → {generated} new pairs generated (total {already + generated}/{args.per_level})\n"
        )

    total = len(all_pairs)
    print(f"Done: {total} QA pairs written to {output_path}")
    by_level = {}
    for p in all_pairs:
        lv = p["level"]
        by_level[lv] = by_level.get(lv, 0) + 1
    for lv in sorted(by_level):
        print(f"  Level {lv}: {by_level[lv]}")


if __name__ == "__main__":
    main()
