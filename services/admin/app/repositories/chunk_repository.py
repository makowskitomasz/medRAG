from medrag_shared.mongo import get_db


async def delete_by_project(project_id: str) -> int:
    result = await get_db().chunks.delete_many({"project_id": project_id})
    return result.deleted_count


async def count_by_project(project_id: str) -> int:
    return await get_db().chunks.count_documents({"project_id": project_id})
