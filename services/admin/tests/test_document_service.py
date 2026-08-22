"""Unit tests for document_service — pagination and filtering logic."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.services.document_service import list_documents


def _make_doc(doc_id: str, status: str = "indexed") -> dict:
    return {
        "_id": doc_id,
        "filename": f"{doc_id}.pdf",
        "status": status,
        "created_at": datetime(2026, 5, 20, tzinfo=UTC),
        "status_history": [],
    }


@pytest.mark.asyncio
async def test_list_returns_correct_page():
    docs = [_make_doc(f"doc-{i}") for i in range(3)]
    with patch(
        "app.repositories.document_repository.list_by_project",
        new_callable=AsyncMock,
        return_value=(docs, 25),
    ):
        result = await list_documents("proj-1", page=1, limit=3, status=None)

    assert result.total == 25
    assert result.page == 1
    assert result.limit == 3
    assert result.pages == 9  # ceil(25/3)
    assert len(result.items) == 3


@pytest.mark.asyncio
async def test_list_pages_calculated_correctly():
    with patch(
        "app.repositories.document_repository.list_by_project",
        new_callable=AsyncMock,
        return_value=([], 10),
    ):
        result = await list_documents("proj-1", page=1, limit=10, status=None)
    assert result.pages == 1

    with patch(
        "app.repositories.document_repository.list_by_project",
        new_callable=AsyncMock,
        return_value=([], 11),
    ):
        result = await list_documents("proj-1", page=1, limit=10, status=None)
    assert result.pages == 2


@pytest.mark.asyncio
async def test_list_empty_project_returns_zero():
    with patch(
        "app.repositories.document_repository.list_by_project",
        new_callable=AsyncMock,
        return_value=([], 0),
    ):
        result = await list_documents("empty-proj", page=1, limit=10, status=None)

    assert result.total == 0
    assert result.pages == 1
    assert result.items == []


@pytest.mark.asyncio
async def test_list_passes_status_filter_to_repository():
    with patch(
        "app.repositories.document_repository.list_by_project",
        new_callable=AsyncMock,
        return_value=([_make_doc("d1", "indexed")], 1),
    ) as mock_repo:
        await list_documents("proj-1", page=1, limit=10, status="indexed")

    mock_repo.assert_called_once_with("proj-1", 1, 10, "indexed")


@pytest.mark.asyncio
async def test_list_document_response_fields():
    doc = _make_doc("doc-x", "parsed")
    with patch(
        "app.repositories.document_repository.list_by_project",
        new_callable=AsyncMock,
        return_value=([doc], 1),
    ):
        result = await list_documents("proj-1", page=1, limit=10, status=None)

    item = result.items[0]
    assert item.document_id == "doc-x"
    assert item.filename == "doc-x.pdf"
    assert item.status == "parsed"
    assert item.status_history == []
