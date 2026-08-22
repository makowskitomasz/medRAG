from medrag_shared.mongo import get_db


async def find_by_ids(chunk_ids: list[str]) -> list[dict]:
    return await get_db().chunks.find({"_id": {"$in": chunk_ids}}).to_list(len(chunk_ids))


async def update_weaviate_id(chunk_id: str, weaviate_id: str) -> None:
    await get_db().chunks.update_one(
        {"_id": chunk_id},
        {"$set": {"weaviate_id": weaviate_id}},
    )
