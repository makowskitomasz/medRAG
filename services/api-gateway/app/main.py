from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from medrag_shared import get_logger

from app.config import settings

logger = get_logger(__name__)
bearer = HTTPBearer()

_http: httpx.AsyncClient | None = None


def get_http() -> httpx.AsyncClient:
    if _http is None:
        raise RuntimeError("HTTP client not initialized")
    return _http


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _http
    _http = httpx.AsyncClient(timeout=30.0)
    logger.info("api-gateway ready")
    yield
    await _http.aclose()


app = FastAPI(title="API Gateway", lifespan=lifespan)


async def validate_jwt(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    http: httpx.AsyncClient = Depends(get_http),
) -> dict:
    try:
        resp = await http.post(
            f"{settings.auth_url}/auth/validate",
            headers={"Authorization": f"Bearer {credentials.credentials}"},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return {**resp.json(), "token": credentials.credentials}
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth service unavailable",
        )


async def _proxy(
    request: Request,
    target_url: str,
    http: httpx.AsyncClient,
    user: dict,
) -> Response:
    headers = dict(request.headers)
    headers["X-User-Id"] = user["user_id"]
    headers["X-User-Role"] = user["role"]
    headers.pop("host", None)

    body = await request.body()
    resp = await http.request(
        method=request.method,
        url=target_url,
        headers=headers,
        content=body,
        params=dict(request.query_params),
    )
    return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))


@app.api_route("/chat/{path:path}", methods=["GET", "POST"])
async def proxy_chat(
    path: str,
    request: Request,
    user: dict = Depends(validate_jwt),
    http: httpx.AsyncClient = Depends(get_http),
) -> Response:
    return await _proxy(request, f"{settings.orchestrator_url}/{path}", http, user)


@app.api_route("/ingest/{path:path}", methods=["GET", "POST", "DELETE"])
async def proxy_ingest(
    path: str,
    request: Request,
    user: dict = Depends(validate_jwt),
    http: httpx.AsyncClient = Depends(get_http),
) -> Response:
    return await _proxy(request, f"{settings.ingestion_url}/{path}", http, user)


@app.api_route("/admin/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_admin(
    path: str,
    request: Request,
    user: dict = Depends(validate_jwt),
    http: httpx.AsyncClient = Depends(get_http),
) -> Response:
    if user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return await _proxy(request, f"{settings.admin_url}/{path}", http, user)


@app.api_route("/auth/{path:path}", methods=["GET", "POST"])
async def proxy_auth(
    path: str, request: Request, http: httpx.AsyncClient = Depends(get_http)
) -> Response:
    body = await request.body()
    resp = await http.request(
        method=request.method,
        url=f"{settings.auth_url}/auth/{path}",
        headers=dict(request.headers),
        content=body,
    )
    return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.service_name}
