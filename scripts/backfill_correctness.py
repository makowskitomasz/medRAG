#!/usr/bin/env python3
"""
Idempotent backfill script: compute answer_correctness for eval_results
that don't have it yet.

Loads gold_answer from benchmark JSON files (since it's not stored in MongoDB).
Safe to run multiple times — skips documents that already have the metric.

Usage:
    python scripts/backfill_correctness.py \
        --input results/hotpotqa_results.json results/hotpotqa_fixed_modes.json \
        --mongo-uri mongodb://localhost:27017 \
        --project-id 6a2150973b2820344a79ba44 \
        --generation-url http://localhost:8006 \
        --concurrency 4
"""

import argparse
import asyncio
import json
from pathlib import Path

import httpx

_JUDGE_MODEL = "openai/gpt-oss-120b"
_BATCH_SIZE = 50


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--input", nargs="+", required=True, help="Benchmark JSON result files")
    p.add_argument("--mongo-uri", default="mongodb://localhost:27017")
    p.add_argument("--project-id", required=True)
    p.add_argument("--generation-url", default="http://localhost:8006")
    p.add_argument("--concurrency", type=int, default=4)
    return p.parse_args()


def _load_gold_answers(paths: list[str]) -> dict[str, str]:
    """Returns {question -> gold_answer} from benchmark JSON files."""
    gold: dict[str, str] = {}
    for path in paths:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        for r in data:
            q = r.get("question", "")
            g = r.get("gold_answer", "")
            if q and g:
                gold[q] = g
    print(f"  Loaded {len(gold)} gold answers from {len(paths)} file(s)")
    return gold


async def _score_one(
    client: httpx.AsyncClient,
    generation_url: str,
    doc_id: str,
    query: str,
    answer: str,
    gold_answer: str,
    sem: asyncio.Semaphore,
) -> tuple[str, float | None]:
    async with sem:
        try:
            resp = await client.post(
                f"{generation_url}/correctness",
                json={
                    "query": query,
                    "answer": answer,
                    "gold_answer": gold_answer,
                    "llm_model": _JUDGE_MODEL,
                },
                timeout=60.0,
            )
            resp.raise_for_status()
            return doc_id, float(resp.json().get("score", 0.0))
        except Exception as exc:
            print(f"  [WARN] {doc_id}: {exc}")
            return doc_id, None


async def main() -> None:
    import bson
    from pymongo import MongoClient, UpdateOne

    args = _parse_args()

    print("Loading gold answers from benchmark files…")
    gold_map = _load_gold_answers(args.input)

    client_mongo = MongoClient(args.mongo_uri, serverSelectionTimeoutMS=3000)
    db = client_mongo["medrag"]

    query_filter = {
        "project_id": args.project_id,
        "eval_mode": "benchmark",
        "metrics.answer_correctness": {"$exists": False},
    }
    total = db["eval_results"].count_documents(query_filter)
    print(f"Documents missing answer_correctness: {total}")
    if total == 0:
        print("Nothing to do.")
        client_mongo.close()
        return

    sem = asyncio.Semaphore(args.concurrency)
    done = skipped = errors = 0

    async with httpx.AsyncClient() as http:
        buf: list[dict] = []

        async def flush(batch: list[dict]) -> None:
            nonlocal done, skipped, errors
            tasks = []
            valid = []
            for doc in batch:
                q = doc.get("question", "")
                a = doc.get("answer", "")
                g = gold_map.get(q, "")
                if not g:
                    skipped += 1
                    continue
                tasks.append(_score_one(http, args.generation_url, str(doc["_id"]), q, a, g, sem))
                valid.append(doc)

            if not tasks:
                return

            results = await asyncio.gather(*tasks)
            ops = []
            for doc_id, score in results:
                if score is None:
                    errors += 1
                    continue
                ops.append(
                    UpdateOne(
                        {"_id": bson.ObjectId(doc_id)},
                        {"$set": {"metrics.answer_correctness": round(score, 4)}},
                    )
                )
                done += 1

            if ops:
                db["eval_results"].bulk_write(ops, ordered=False)

            print(
                f"  updated={done}  skipped(no gold)={skipped}  errors={errors}  remaining≈{total - done - skipped - errors}"
            )

        for doc in db["eval_results"].find(query_filter, {"_id": 1, "question": 1, "answer": 1}):
            buf.append(doc)
            if len(buf) >= _BATCH_SIZE:
                await flush(buf)
                buf = []
        if buf:
            await flush(buf)

    print(f"\nDone. Updated: {done}, Skipped (no gold): {skipped}, Errors: {errors}")
    client_mongo.close()


if __name__ == "__main__":
    asyncio.run(main())
