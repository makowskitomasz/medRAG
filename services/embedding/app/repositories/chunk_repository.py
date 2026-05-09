from medrag_shared.mongo import get_db


async def find_by_ids(chunk_ids: list[str]) -> list[dict]:
    return await get_db().chunks.find({"_id": {"$in": chunk_ids}}).to_list(len(chunk_ids))
