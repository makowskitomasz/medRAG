from medrag_shared.mongo import get_db


async def list_by_project(
    project_id: str,
    page: int = 1,
    limit: int = 10,
    status: str | None = None,
) -> tuple[list[dict], int]:
    query: dict = {"project_id": project_id}
    if status:
        query["status"] = status
    skip = (page - 1) * limit
    total = await get_db().documents.count_documents(query)
    docs = (
        await get_db()
        .documents.find(query, {"extracted_text": 0})
        .skip(skip)
        .limit(limit)
        .to_list(limit)
    )
    return docs, total


async def find_indexed_by_project(project_id: str) -> list[dict]:
    return (
        await get_db()
        .documents.find(
            {"project_id": project_id, "status": "indexed"},
            {"_id": 1, "filename": 1, "content_hash": 1},
        )
        .to_list(1000)
    )


async def delete_by_project(project_id: str) -> int:
    result = await get_db().documents.delete_many({"project_id": project_id})
    return result.deleted_count
