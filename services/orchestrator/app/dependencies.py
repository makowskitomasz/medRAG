from collections.abc import AsyncGenerator

import httpx
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.connectors import get_db_instance, get_http_client_instance


async def get_db() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    yield get_db_instance()


async def get_http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    yield get_http_client_instance()
