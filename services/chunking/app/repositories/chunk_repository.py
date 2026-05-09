from medrag_shared.models.document import Chunk
from medrag_shared.mongo import get_db


async def insert_many(chunks: list[Chunk]) -> None:
    if chunks:
        await get_db().chunks.insert_many([c.model_dump(by_alias=True) for c in chunks])
