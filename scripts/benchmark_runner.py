#!/usr/bin/env python3
"""
Benchmark runner for medRAG evaluation.

Usage:
    python scripts/benchmark_runner.py \\
        --dataset data/hotpotqa_1000.json \\
        --project-id <PROJECT_ID> \\
        --token <JWT_TOKEN> \\
        [--modes vanilla,hyde,query_rewriting] \\
        [--concurrency 3] \\
        [--dry-run] \\
        [--output results/hotpotqa_results.json]

Dataset JSON format:
    [{"question": "...", "gold_answer": "...", ...}, ...]

For each (rag_mode, qa_pair): streams /chat/query/stream, measures latency,
saves results incrementally so no data is lost on crash.
"""

import argparse
import asyncio
import json
import os
import time
from pathlib import Path

import httpx

RAG_MODES = [
    "vanilla",
    "hyde",
    "query_rewriting",
    "self_reflection",
    "multi_agent",
    "corrective_rag",
    "iterative_multihop",
    "madam_rag",
    "rare_rag",
]

# Approximate cost per 1k tokens in USD (claude-haiku-4-5 estimate)
_COST_PER_1K_TOKENS = 0.003
_DRY_RUN_LIMIT = 10


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="medRAG benchmark runner")
    # Primary args (new names)
    p.add_argument("--dataset", dest="dataset", help="Path to JSON file with QA pairs")
    p.add_argument(
        "--modes",
        dest="modes",
        help="Comma-separated RAG modes to evaluate (default: all)",
    )
    # Legacy aliases kept for backward compatibility
    p.add_argument("--qa-file", dest="qa_file", help=argparse.SUPPRESS)
    p.add_argument("--rag-modes", dest="rag_modes", nargs="+", help=argparse.SUPPRESS)

    p.add_argument("--project-id", required=True, help="Admin project ID (MongoDB ObjectId)")
    p.add_argument("--gateway-url", default="http://localhost:8000", help="API gateway base URL")
    p.add_argument("--token", required=True, help="JWT bearer token")
    p.add_argument(
        "--model",
        default=None,
        help="LLM model override sent as X-LLM-Model header",
    )
    p.add_argument(
        "--judge-model",
        default="anthropic/claude-haiku-4-5",
        help="Model for LLM-as-judge evaluation (informational, eval service decides)",
    )
    p.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Max parallel queries per mode (default: 1)",
    )
    p.add_argument(
        "--output",
        default="benchmark_results.json",
        help="Output JSON file path (written incrementally)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help=f"Process only first {_DRY_RUN_LIMIT} questions per mode, skip Mongo write",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of questions per mode (overrides --dry-run limit)",
    )
    p.add_argument(
        "--mongo-uri",
        default=os.environ.get("MONGO_URI", "mongodb://localhost:27017"),
        help="MongoDB URI for eval metrics enrichment (default: mongodb://localhost:27017)",
    )
    p.add_argument(
        "--eval-wait",
        type=int,
        default=0,
        help="Seconds to wait for eval service before fetching metrics (default: auto = 2s per query)",
    )
    # Legacy
    p.add_argument("--eval-delay", type=float, default=0.0, help=argparse.SUPPRESS)
    return p.parse_args()


def _resolve_qa_path(args: argparse.Namespace) -> str:
    if args.dataset:
        return args.dataset
    if args.qa_file:
        return args.qa_file
    raise SystemExit("--dataset is required")


def _resolve_modes(args: argparse.Namespace) -> list[str]:
    # New --modes=vanilla,hyde
    if args.modes:
        candidates = [m.strip() for m in args.modes.split(",") if m.strip()]
        invalid = [m for m in candidates if m not in RAG_MODES]
        if invalid:
            raise SystemExit(f"Unknown RAG modes: {invalid}. Valid: {RAG_MODES}")
        return candidates
    # Legacy --rag-modes vanilla hyde
    if args.rag_modes:
        return args.rag_modes
    return RAG_MODES


def _set_rag_mode(
    client: httpx.Client, gateway_url: str, project_id: str, rag_mode: str, token: str
) -> None:
    resp = client.patch(
        f"{gateway_url}/admin/projects/{project_id}/settings",
        json={"rag_mode": rag_mode},
        headers={"Authorization": f"Bearer {token}"},
        timeout=30.0,
    )
    resp.raise_for_status()


async def _query(
    client: httpx.AsyncClient,
    gateway_url: str,
    project_id: str,
    question: str,
    gold_answer: str,
    token: str,
    model: str | None,
    qa_metadata: dict | None = None,
) -> dict:
    """POST /chat/query (non-streaming) — triggers RabbitMQ publish for eval metrics."""
    headers: dict[str, str] = {"Authorization": f"Bearer {token}"}
    if model:
        headers["X-LLM-Model"] = model

    gold_context_titles: list[str] = [
        d["title"] for d in (qa_metadata or {}).get("supporting_docs", []) if d.get("title")
    ]
    payload: dict = {
        "project_id": project_id,
        "query": question,
        "gold_answer": gold_answer,
        "gold_context_titles": gold_context_titles,
    }

    start = time.monotonic()
    resp = await client.post(
        f"{gateway_url}/chat/query",
        json=payload,
        headers=headers,
        timeout=300.0,
    )
    resp.raise_for_status()
    latency_ms = int((time.monotonic() - start) * 1000)

    data = resp.json()
    answer: str = data.get("answer", "")
    citations: list[dict] = data.get("citations", [])
    rag_mode_resp: str = data.get("rag_mode", "")
    conversation_id: str = data.get("conversation_id", "")
    token_count: int = len(answer.split())

    return {
        "question": question,
        "gold_answer": gold_answer,
        "rag_mode": rag_mode_resp,
        "answer": answer,
        "citations": citations,
        "latency_ms": latency_ms,
        "token_count": token_count,
        "conversation_id": conversation_id,
        "eval_result_id": None,
        "metadata": qa_metadata or {},
    }


def _append_result(output_path: Path, result: dict) -> None:
    """Append a single result to the output JSON file (read-modify-write)."""
    if output_path.exists():
        existing: list[dict] = json.loads(output_path.read_text(encoding="utf-8"))
    else:
        existing = []
    existing.append(result)
    output_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")


async def _run_mode(
    mode: str,
    qa_pairs: list[dict],
    args: argparse.Namespace,
    output_path: Path,
    sync_client: httpx.Client,
    write_lock: asyncio.Lock,
    completed: set[tuple[str, str]] | None = None,
) -> list[dict]:
    """Run all QA pairs for one RAG mode and return results."""
    print(f"\n── Mode: {mode} ──────────────────────────────")

    limit = args.limit if args.limit else (_DRY_RUN_LIMIT if args.dry_run else None)
    pairs = qa_pairs[:limit] if limit else qa_pairs

    # Skip already-completed (question, mode) pairs when resuming
    if completed:
        remaining = [p for p in pairs if (mode, p["question"]) not in completed]
        skipped = len(pairs) - len(remaining)
        if skipped:
            print(f"  Skipping {skipped} already-completed questions")
        pairs = remaining

    if not pairs:
        print(f"  All questions already done for {mode}, skipping.")
        return []

    try:
        _set_rag_mode(sync_client, args.gateway_url, args.project_id, mode, args.token)
    except httpx.HTTPStatusError as exc:
        print(f"  [WARN] Could not set rag_mode={mode}: {exc}")
        return []
    semaphore = asyncio.Semaphore(args.concurrency)
    results: list[dict] = []

    async def _process(i: int, pair: dict) -> dict | None:
        question = pair["question"]
        gold_answer = pair.get("gold_answer", "")
        qa_metadata = {
            k: v for k, v in pair.items() if k not in ("question", "gold_answer", "context")
        }
        print(f"  [{i}/{len(pairs)}] {question[:70]}…")
        async with semaphore, httpx.AsyncClient() as aclient:
            try:
                result = await _query(
                    aclient,
                    args.gateway_url,
                    args.project_id,
                    question,
                    gold_answer,
                    args.token,
                    args.model,
                    qa_metadata,
                )
                result["rag_mode"] = mode  # ensure mode is set even if stream returns ""
                async with write_lock:
                    _append_result(output_path, result)
                return result
            except Exception as exc:
                err: dict = {
                    "question": question,
                    "gold_answer": gold_answer,
                    "rag_mode": mode,
                    "error": str(exc),
                    "latency_ms": None,
                    "token_count": 0,
                }
                print(f"  [ERROR] {exc}")
                async with write_lock:
                    _append_result(output_path, err)
                return err

    tasks = [_process(i, pair) for i, pair in enumerate(pairs, 1)]
    raw = await asyncio.gather(*tasks)
    results = [r for r in raw if r is not None]
    return results


def _enrich_from_mongo(results: list[dict], mongo_uri: str, project_id: str) -> list[dict]:
    """Fetch eval metrics from MongoDB and add them to each result dict."""
    try:
        from pymongo import MongoClient  # type: ignore[import]
    except ImportError:
        print("  [WARN] pymongo not installed — skipping eval enrichment")
        return results

    try:
        client: MongoClient = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
        client.admin.command("ping")
    except Exception as exc:
        print(f"  [WARN] Cannot connect to MongoDB ({exc}) — skipping enrichment")
        return results

    db = client["medrag"]
    # Build lookup: (question, rag_mode) → eval_result
    eval_docs = list(
        db["eval_results"].find(
            {"project_id": project_id},
            {"_id": 1, "question": 1, "rag_mode": 1, "metrics": 1},
        )
    )
    lookup: dict[tuple[str, str], dict] = {
        (d["question"].strip(), d["rag_mode"]): d for d in eval_docs
    }
    client.close()

    enriched = 0
    for r in results:
        key = (r.get("question", "").strip(), r.get("rag_mode", ""))
        match = lookup.get(key)
        if match:
            r["eval_result_id"] = str(match["_id"])
            for metric, val in match.get("metrics", {}).items():
                r[metric] = val
            enriched += 1

    print(f"  Enriched {enriched}/{len(results)} results with eval metrics from MongoDB")
    return results


def _print_summary(
    results: list[dict], total_seconds: float, output_path: Path | None = None
) -> None:
    from collections import defaultdict

    by_mode: dict = defaultdict(list)
    for r in results:
        if "error" not in r:
            by_mode[r.get("rag_mode", "unknown")].append(r)

    metrics = [
        "token_f1",
        "em",
        "rouge_l",
        "faithfulness",
        "answer_relevance",
        "context_recall",
        "latency_ms",
    ]
    header = f"{'rag_mode':<25}" + "".join(f"{m:>18}" for m in metrics) + f"{'n':>6}"
    sep = "=" * len(header)
    print(f"\n{sep}\n{header}\n{sep}")

    for mode in RAG_MODES:
        if mode not in by_mode:
            continue
        rows = by_mode[mode]
        row_str = f"{mode:<25}"
        for m in metrics:
            vals = [r.get(m) for r in rows if r.get(m) is not None]
            row_str += f"{sum(vals) / len(vals):>18.4f}" if vals else f"{'N/A':>18}"
        row_str += f"{len(rows):>6}"
        print(row_str)
    print(sep)

    total_queries = sum(len(v) for v in by_mode.values())
    total_tokens = sum(r.get("token_count", 0) for r in results if "error" not in r)
    est_cost = total_tokens / 1000 * _COST_PER_1K_TOKENS
    footer = (
        f"\nSummary: {total_queries} queries across {len(by_mode)} modes "
        f"in {total_seconds:.1f}s | tokens: {total_tokens} | "
        f"est. cost: ${est_cost:.4f}"
    )
    print(footer)

    if output_path:
        summary_path = output_path.with_suffix(".summary.txt")
        lines = [sep, header, sep]
        for mode in RAG_MODES:
            if mode not in by_mode:
                continue
            rows = by_mode[mode]
            row_str = f"{mode:<25}"
            for m in metrics:
                vals = [r.get(m) for r in rows if r.get(m) is not None]
                row_str += f"{sum(vals) / len(vals):>18.4f}" if vals else f"{'N/A':>18}"
            row_str += f"{len(rows):>6}"
            lines.append(row_str)
        lines += [sep, footer]
        summary_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"Summary saved → {summary_path}")


async def async_main() -> None:
    args = _parse_args()

    qa_path = _resolve_qa_path(args)
    modes = _resolve_modes(args)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    qa_pairs: list[dict] = json.loads(Path(qa_path).read_text(encoding="utf-8"))
    (min(len(qa_pairs), _DRY_RUN_LIMIT) if args.dry_run else len(qa_pairs))

    # Fetch project settings to display active model
    try:
        with httpx.Client() as _c:
            _resp = _c.get(
                f"{args.gateway_url}/admin/projects/{args.project_id}",
                headers={"Authorization": f"Bearer {args.token}"},
                timeout=10.0,
            )
            _resp.raise_for_status()
            _proj = _resp.json()
            active_model = args.model or _proj.get("settings", {}).get("llm_model", "unknown")
    except Exception:
        active_model = args.model or "unknown (could not fetch project settings)"

    print(f"Dataset:   {qa_path}  ({len(qa_pairs)} pairs)")
    print(f"Modes:     {modes}")
    limit_display = args.limit or (_DRY_RUN_LIMIT if args.dry_run else len(qa_pairs))
    print(f"Queries:   {len(modes)} × {limit_display} = {len(modes) * limit_display}")
    print(f"Model:     {active_model}")
    if args.dry_run:
        print("Mode:      DRY-RUN")
    print(f"Output:    {output_path}")
    print()

    # Resume: load already-completed results to skip them
    completed: set[tuple[str, str]] = set()
    if output_path.exists() and not args.dry_run:
        try:
            existing = json.loads(output_path.read_text(encoding="utf-8"))
            for r in existing:
                if "error" not in r and r.get("answer"):
                    completed.add((r["rag_mode"], r["question"]))
            if completed:
                print(f"Resuming: {len(completed)} results already in {output_path}")
        except Exception:
            output_path.write_text("[]", encoding="utf-8")
    elif not output_path.exists() or args.dry_run:
        output_path.write_text("[]", encoding="utf-8")

    write_lock = asyncio.Lock()
    all_results: list[dict] = []
    start_ts = time.monotonic()

    with httpx.Client() as sync_client:
        for mode in modes:
            mode_results = await _run_mode(
                mode,
                qa_pairs,
                args,
                output_path,
                sync_client,
                write_lock,
                completed=completed,
            )
            all_results.extend(mode_results)

    total_seconds = time.monotonic() - start_ts

    # Wait for eval service to process RabbitMQ events, then enrich with metrics
    if not args.dry_run and all_results:
        n_queries = len([r for r in all_results if "error" not in r])
        eval_wait = args.eval_wait if args.eval_wait > 0 else max(60, n_queries // 2)
        print(f"\nWaiting {eval_wait}s for eval service to process {n_queries} results…")
        await asyncio.sleep(eval_wait)
        print("Fetching eval metrics from MongoDB…")
        all_results = _enrich_from_mongo(all_results, args.mongo_uri, args.project_id)
        # Overwrite output file with enriched results
        output_path.write_text(
            json.dumps(all_results, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    print(f"\nAll results saved → {output_path}")
    _print_summary(all_results, total_seconds, output_path)


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
