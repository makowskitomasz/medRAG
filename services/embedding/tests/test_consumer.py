from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.connectors.providers.base import BaseEmbeddingProvider
from app.services.embedding_service import embed


class FakeProvider(BaseEmbeddingProvider):
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]


@pytest.fixture()
def mock_db():
    db = MagicMock()
    with (
        patch("app.repositories.chunk_repository.get_db", return_value=db),
        patch("app.repositories.document_repository.get_db", return_value=db),
    ):
        yield db


@pytest.fixture(autouse=True)
def mock_publish():
    with patch("app.services.embedding_service.publish", new_callable=AsyncMock):
        yield


async def test_embed_batch(mock_db):
    mock_db.chunks.find.return_value.to_list = AsyncMock(
        return_value=[
            {"_id": "c1", "content": "text one"},
            {"_id": "c2", "content": "text two"},
        ]
    )
    mock_db.documents.update_one = AsyncMock()

    await embed(
        document_id="d1",
        project_id="p1",
        chunk_ids=["c1", "c2"],
        trace_id="trace-1",
        provider=FakeProvider(),
    )

    mock_db.documents.update_one.assert_called_once()


async def test_no_chunks_skips(mock_db):
    mock_db.chunks.find.return_value.to_list = AsyncMock(return_value=[])
    mock_db.documents.update_one = AsyncMock()

    await embed(
        document_id="d1",
        project_id="p1",
        chunk_ids=[],
        trace_id=None,
        provider=FakeProvider(),
    )

    mock_db.documents.update_one.assert_not_called()
