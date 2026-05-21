import csv
import io

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.services import eval_service

router = APIRouter(prefix="/eval-results")


@router.get("")
async def list_eval_results(
    project_id: str | None = Query(default=None),
    rag_mode: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    return await eval_service.list_results(project_id, rag_mode, page, limit)


@router.get("/summary")
async def eval_summary(
    project_id: str | None = Query(default=None),
) -> dict:
    return await eval_service.get_summary(project_id)


@router.get("/export")
async def export_csv(
    project_id: str | None = Query(default=None),
    rag_mode: str | None = Query(default=None),
) -> StreamingResponse:
    rows, fieldnames = await eval_service.export_csv_rows(project_id, rag_mode)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=eval_results.csv"},
    )
