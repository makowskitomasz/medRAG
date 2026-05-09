from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase


_client: AsyncIOMotorClient | None = None


async def connect(uri: str) -> None:
    global _client
    _client = AsyncIOMotorClient(uri)


async def disconnect() -> None:
    global _client
    if _client:
        _client.close()
        _client = None


def get_db(name: str = "medrag") -> AsyncIOMotorDatabase:
    if _client is None:
        raise RuntimeError("MongoDB client not initialized — call connect() first")
    return _client[name]
