import math
from datetime import datetime

from fastapi import APIRouter, Query
from medrag_shared.mongo import get_db

router = APIRouter(prefix="/results")


@router.get("")
async def list_results(
    project_id: str | None = Query(default=None),
    rag_mode: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
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


@router.get("/by-conversation/{conversation_id}")
async def by_conversation(conversation_id: str) -> dict:
    """Metrics for every answer in one conversation, oldest first.

    The chat view pairs these with assistant messages by position, so ordering
    matches the order the answers were produced.
    """
    docs = (
        await get_db()
        .eval_results.find({"conversation_id": conversation_id})
        .sort("timestamp", 1)
        .to_list(200)
    )
    items = []
    for d in docs:
        ts = d.get("timestamp")
        items.append(
            {
                "id": str(d.pop("_id")),
                "rag_mode": d.get("rag_mode"),
                "question": d.get("question"),
                "metrics": d.get("metrics", {}),
                "timestamp": ts.isoformat() if isinstance(ts, datetime) else ts,
            }
        )
    return {"items": items}


@router.get("/summary")
async def summary(
    project_id: str | None = Query(default=None),
) -> dict:
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
    summary_rows = []
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
        summary_rows.append(entry)
    return {"summary": summary_rows}
