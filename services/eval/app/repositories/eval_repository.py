from datetime import UTC, datetime

from medrag_shared.mongo import get_db


async def save(
    project_id: str,
    question: str,
    answer: str,
    rag_mode: str,
    eval_mode: str,
    metrics: dict,
    conversation_id: str | None = None,
    trace_id: str | None = None,
) -> str:
    doc = {
        "project_id": project_id,
        "conversation_id": conversation_id,
        "question": question,
        "answer": answer,
        "rag_mode": rag_mode,
        "eval_mode": eval_mode,
        "metrics": metrics,
        "trace_id": trace_id,
        "timestamp": datetime.now(UTC),
    }
    result = await get_db().eval_results.insert_one(doc)
    return str(result.inserted_id)


async def ensure_indexes() -> None:
    await get_db().eval_results.create_index("project_id")
    await get_db().eval_results.create_index("rag_mode")
    await get_db().eval_results.create_index("timestamp")
