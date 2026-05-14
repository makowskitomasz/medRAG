from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from weaviate import WeaviateAsyncClient

_mongo_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None
_weaviate_client: WeaviateAsyncClient | None = None


def get_db_instance() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("MongoDB not connected")
    return _db


def get_weaviate_instance() -> WeaviateAsyncClient:
    if _weaviate_client is None:
        raise RuntimeError("Weaviate not connected")
    return _weaviate_client


async def connect_mongo(uri: str) -> None:
    global _mongo_client, _db
    _mongo_client = AsyncIOMotorClient(uri)
    _db = _mongo_client.get_default_database()


async def disconnect_mongo() -> None:
    global _mongo_client, _db
    if _mongo_client:
        _mongo_client.close()
        _mongo_client = None
        _db = None


async def connect_weaviate(url: str) -> None:
    import weaviate

    global _weaviate_client
    _weaviate_client = weaviate.use_async_with_local(
        host=url.replace("http://", "").split(":")[0],
        port=int(url.split(":")[-1]),
    )
    await _weaviate_client.connect()


async def disconnect_weaviate() -> None:
    global _weaviate_client
    if _weaviate_client:
        await _weaviate_client.close()
        _weaviate_client = None
