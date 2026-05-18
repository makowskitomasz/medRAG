import math
from datetime import datetime

from medrag_shared.mongo import get_db


def _flatten_metrics(result: dict) -> dict:
    row: dict = {
        "id": str(result["_id"]),
        "rag_mode": result.get("rag_mode", ""),
        "project_id": result.get("project_id", ""),
        "eval_mode": result.get("eval_mode", ""),
        "question": result.get("question", ""),
        "timestamp": result.get("timestamp", ""),
    }
    for k, v in result.get("metrics", {}).items():
        row[k] = v
    return row


async def list_results(
    project_id: str | None,
    rag_mode: str | None,
    page: int,
    limit: int,
) -> dict:
    query: dict = {}
    if project_id:
        query["project_id"] = project_id
    if rag_mode:
        query["rag_mode"] = rag_mode
    skip = (page - 1) * limit
    total = await get_db().eval_results.count_documents(query)
    docs = (
        await get_db()
        .eval_results.find(query)
        .sort("timestamp", -1)
        .skip(skip)
        .limit(limit)
        .to_list(limit)
    )
    items = []
    for d in docs:
        d["id"] = str(d.pop("_id"))
        if isinstance(d.get("timestamp"), datetime):
            d["timestamp"] = d["timestamp"].isoformat()
        items.append(d)
    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": max(1, math.ceil(total / limit)),
    }


async def get_summary(project_id: str | None) -> dict:
    match: dict = {}
    if project_id:
        match["project_id"] = project_id

    pipeline = [
        *(([{"$match": match}]) if match else []),
        {
            "$group": {
                "_id": "$rag_mode",
                "count": {"$sum": 1},
                "avg_faithfulness": {"$avg": "$metrics.faithfulness"},
                "avg_answer_relevance": {"$avg": "$metrics.answer_relevance"},
                "avg_token_f1": {"$avg": "$metrics.token_f1"},
                "avg_latency_ms": {"$avg": "$metrics.latency_ms"},
                "avg_citation_precision": {"$avg": "$metrics.citation_precision"},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    rows = await get_db().eval_results.aggregate(pipeline).to_list(100)
    summary = []
    for r in rows:
        entry = {"rag_mode": r["_id"], "count": r["count"]}
        for k in (
            "avg_faithfulness",
            "avg_answer_relevance",
            "avg_token_f1",
            "avg_latency_ms",
            "avg_citation_precision",
        ):
            v = r.get(k)
            entry[k] = round(v, 4) if v is not None else None
        summary.append(entry)
    return {"summary": summary}


async def export_csv_rows(
    project_id: str | None,
    rag_mode: str | None,
) -> tuple[list[dict], list[str]]:
    query: dict = {}
    if project_id:
        query["project_id"] = project_id
    if rag_mode:
        query["rag_mode"] = rag_mode
    docs = await get_db().eval_results.find(query).sort("timestamp", -1).to_list(10000)

    fieldnames = [
        "id",
        "rag_mode",
        "project_id",
        "eval_mode",
        "question",
        "timestamp",
        "faithfulness",
        "answer_relevance",
        "token_f1",
        "em",
        "context_relevance",
        "citation_precision",
        "latency_ms",
        "token_count",
    ]
    rows = [_flatten_metrics(d) for d in docs]
    return rows, fieldnames
