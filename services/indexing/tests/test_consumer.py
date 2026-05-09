from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.indexing_service import index


@pytest.fixture(autouse=True)
def mock_deps():
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_collection.data.insert_many.return_value = MagicMock(uuids={0: "uuid-1"})
    mock_client = MagicMock()
    mock_client.collections.get.return_value = mock_collection

    with (
        patch("app.repositories.chunk_repository.get_db", return_value=mock_db),
        patch("app.repositories.document_repository.get_db", return_value=mock_db),
        patch("app.services.indexing_service.get_client", return_value=mock_client),
    ):
        mock_db.chunks.find.return_value.to_list = AsyncMock(
            return_value=[{"_id": "c1", "content": "hello", "chunk_index": 0}]
        )
        mock_db.chunks.update_one = AsyncMock()
        mock_db.documents.update_one = AsyncMock()
        yield mock_db


async def test_index_chunks(mock_deps):
    await index(
        document_id="d1",
        project_id="p1",
        embeddings=[{"chunk_id": "c1", "vector": [0.1, 0.2]}],
        trace_id="t1",
    )
    mock_deps.documents.update_one.assert_called_once()


async def test_empty_embeddings(mock_deps):
    mock_deps.chunks.find.return_value.to_list = AsyncMock(return_value=[])
    await index(
        document_id="d1",
        project_id="p1",
        embeddings=[],
        trace_id=None,
    )
    mock_deps.documents.update_one.assert_called_once()
