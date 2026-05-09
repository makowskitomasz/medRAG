import httpx

_client: httpx.AsyncClient | None = None


def get_http() -> httpx.AsyncClient:
    if _client is None:
        raise RuntimeError("HTTP client not initialized")
    return _client


async def connect() -> None:
    global _client
    _client = httpx.AsyncClient(timeout=30.0)


async def disconnect() -> None:
    global _client
    if _client:
        await _client.aclose()
        _client = None
