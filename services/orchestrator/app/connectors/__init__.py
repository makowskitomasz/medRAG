import httpx
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

_mongo_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None
_http_client: httpx.AsyncClient | None = None


def get_db_instance() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("MongoDB not connected")
    return _db


def get_http_client_instance() -> httpx.AsyncClient:
    if _http_client is None:
        raise RuntimeError("HTTP client not initialized")
    return _http_client


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


async def create_http_client() -> None:
    global _http_client
    _http_client = httpx.AsyncClient(timeout=120.0)


async def close_http_client() -> None:
    global _http_client
    if _http_client:
        await _http_client.aclose()
        _http_client = None
