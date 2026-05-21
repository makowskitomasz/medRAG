import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.config import settings
from app.connectors.http_connector import get_http
from app.dependencies import require_auth
from app.services.proxy_service import proxy

router = APIRouter()


@router.api_route("/chat/{path:path}", methods=["GET", "POST"])
async def proxy_chat(
    path: str,
    request: Request,
    user: dict = Depends(require_auth),
    http: httpx.AsyncClient = Depends(get_http),
) -> Response:
    return await proxy(request, f"{settings.orchestrator_url}/{path}", http, user)


@router.api_route("/ingest/{path:path}", methods=["GET", "POST", "DELETE"])
async def proxy_ingest(
    path: str,
    request: Request,
    user: dict = Depends(require_auth),
    http: httpx.AsyncClient = Depends(get_http),
) -> Response:
    return await proxy(request, f"{settings.ingestion_url}/{path}", http, user)


@router.api_route("/admin/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_admin(
    path: str,
    request: Request,
    user: dict = Depends(require_auth),
    http: httpx.AsyncClient = Depends(get_http),
) -> Response:
    if user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return await proxy(request, f"{settings.admin_url}/{path}", http, user)


@router.api_route("/eval/{path:path}", methods=["GET", "POST"])
async def proxy_eval(
    path: str,
    request: Request,
    user: dict = Depends(require_auth),
    http: httpx.AsyncClient = Depends(get_http),
) -> Response:
    return await proxy(request, f"{settings.eval_url}/{path}", http, user)


@router.api_route("/auth/{path:path}", methods=["GET", "POST"])
async def proxy_auth(
    path: str,
    request: Request,
    http: httpx.AsyncClient = Depends(get_http),
) -> Response:
    body = await request.body()
    resp = await http.request(
        method=request.method,
        url=f"{settings.auth_url}/auth/{path}",
        headers=dict(request.headers),
        content=body,
    )
    return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))
