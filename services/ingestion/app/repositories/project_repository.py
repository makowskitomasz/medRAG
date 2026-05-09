from medrag_shared.mongo import get_db


async def find_by_id(project_id: str) -> dict | None:
    return await get_db().projects.find_one({"_id": project_id})
