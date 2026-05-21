#!/usr/bin/env python3
"""
Benchmark runner for medRAG evaluation.

Usage:
    python scripts/benchmark_runner.py \\
        --qa-file scripts/qa_pairs.json \\
        --project-id <PROJECT_ID> \\
        --gateway-url http://localhost:8000 \\
        --token <JWT_TOKEN> \\
        [--rag-modes vanilla hyde query_rewriting self_reflection ...]
        [--output results.json]

QA pairs JSON format:
    [{"question": "...", "gold_answer": "..."}, ...]

For each (rag_mode, qa_pair): POSTs to /chat/query with gold_answer,
waits for eval_service to persist the result, then prints a summary table.
"""

import argparse
import json
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


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="medRAG benchmark runner")
    p.add_argument("--qa-file", required=True, help="Path to JSON file with QA pairs")
    p.add_argument("--project-id", required=True, help="Admin project ID to use")
    p.add_argument(
        "--gateway-url", default="http://localhost:8000", help="API gateway base URL"
    )
    p.add_argument("--token", required=True, help="JWT bearer token")
    p.add_argument(
        "--rag-modes",
        nargs="+",
        default=RAG_MODES,
        choices=RAG_MODES,
        metavar="MODE",
        help="RAG modes to evaluate (default: all 9)",
    )
    p.add_argument(
        "--output", default="benchmark_results.json", help="Output JSON file path"
    )
    p.add_argument(
        "--eval-delay",
        type=float,
        default=5.0,
        help="Seconds to wait after each query for eval_service to process (default: 5)",
    )
    return p.parse_args()


def _set_rag_mode(
    client: httpx.Client, gateway_url: str, project_id: str, rag_mode: str, token: str
) -> None:
    resp = client.patch(
        f"{gateway_url}/admin/projects/{project_id}/settings",
        json={"rag_mode": rag_mode},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp.raise_for_status()


def _send_query(
    client: httpx.Client,
    gateway_url: str,
    project_id: str,
    question: str,
    gold_answer: str,
    token: str,
) -> dict:
    resp = client.post(
        f"{gateway_url}/chat/query",
        json={
            "project_id": project_id,
            "query": question,
            "gold_answer": gold_answer,
        },
        headers={"Authorization": f"Bearer {token}"},
        timeout=120.0,
    )
    resp.raise_for_status()
    return resp.json()


def _print_summary(results: list[dict]) -> None:
    from collections import defaultdict

    by_mode: dict = defaultdict(list)
    for r in results:
        by_mode[r["rag_mode"]].append(r)

    metrics = ["token_f1", "em", "faithfulness", "answer_relevance", "latency_ms"]
    header = f"{'rag_mode':<25}" + "".join(f"{m:>18}" for m in metrics)
    print("\n" + "=" * len(header))
    print(header)
    print("=" * len(header))

    for mode in RAG_MODES:
        if mode not in by_mode:
            continue
        rows = by_mode[mode]
        n = len(rows)
        row_str = f"{mode:<25}"
        for m in metrics:
            vals = [r.get(m) for r in rows if r.get(m) is not None]
            if vals:
                avg = sum(vals) / len(vals)
                row_str += f"{avg:>18.4f}"
            else:
                row_str += f"{'N/A':>18}"
        row_str += f"  (n={n})"
        print(row_str)
    print("=" * len(header))


def main() -> None:
    args = _parse_args()

    qa_pairs: list[dict] = json.loads(Path(args.qa_file).read_text())
    print(f"Loaded {len(qa_pairs)} QA pairs from {args.qa_file}")
    print(
        f"Running {len(args.rag_modes)} RAG modes × {len(qa_pairs)} questions "
        f"= {len(args.rag_modes) * len(qa_pairs)} total queries\n"
    )

    all_results: list[dict] = []

    with httpx.Client() as client:
        for mode in args.rag_modes:
            print(f"\n── Mode: {mode} ──────────────────────────────")
            try:
                _set_rag_mode(
                    client, args.gateway_url, args.project_id, mode, args.token
                )
            except httpx.HTTPStatusError as exc:
                print(f"  [WARN] Could not set rag_mode={mode}: {exc}")
                continue

            for i, pair in enumerate(qa_pairs, 1):
                question = pair["question"]
                gold_answer = pair.get("gold_answer", "")
                print(f"  [{i}/{len(qa_pairs)}] {question[:60]}...")
                try:
                    resp = _send_query(
                        client,
                        args.gateway_url,
                        args.project_id,
                        question,
                        gold_answer,
                        args.token,
                    )
                    row = {
                        "rag_mode": mode,
                        "question": question,
                        "answer": resp.get("answer", ""),
                        "latency_ms": resp.get("latency_ms"),
                    }
                    all_results.append(row)
                    time.sleep(args.eval_delay)
                except Exception as exc:
                    print(f"  [ERROR] {exc}")
                    all_results.append(
                        {"rag_mode": mode, "question": question, "error": str(exc)}
                    )

    Path(args.output).write_text(json.dumps(all_results, indent=2, ensure_ascii=False))
    print(f"\nRaw results saved to {args.output}")
    _print_summary([r for r in all_results if "error" not in r])


if __name__ == "__main__":
    main()
