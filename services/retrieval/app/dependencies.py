from collections.abc import AsyncGenerator

from motor.motor_asyncio import AsyncIOMotorDatabase
from weaviate import WeaviateAsyncClient

from app.connectors import get_db_instance, get_weaviate_instance


async def get_db() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    yield get_db_instance()


async def get_weaviate() -> AsyncGenerator[WeaviateAsyncClient, None]:
    yield get_weaviate_instance()
