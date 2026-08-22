"""Unit tests for benchmark_runner.py."""

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import benchmark_runner as br

# ---------------------------------------------------------------------------
# SSE parsing helpers
# ---------------------------------------------------------------------------


def _make_sse_lines(
    tokens: list[str], citations: list[dict], rag_mode: str = "vanilla"
) -> list[str]:
    lines: list[str] = []
    lines.append(f"data: {json.dumps({'type': 'search', 'status': 'start'})}")
    lines.append(f"data: {json.dumps({'type': 'search', 'status': 'done', 'count': 1})}")
    for t in tokens:
        lines.append(f"data: {json.dumps({'type': 'token', 'content': t})}")
    lines.append(
        f"data: {json.dumps({'type': 'citations', 'citations': citations, 'rag_mode': rag_mode, 'conversation_id': 'conv-1'})}"
    )
    lines.append("data: [DONE]")
    return lines


class _FakeStreamCtx:
    """Mimics httpx.AsyncClient.stream() async context manager."""

    def __init__(self, lines: list[str]) -> None:
        self._lines = lines

    async def __aenter__(self) -> "_FakeStreamCtx":
        self.status_code = 200
        return self

    async def __aexit__(self, *args: object) -> None:
        pass

    def raise_for_status(self) -> None:
        pass

    async def aiter_lines(self):
        for line in self._lines:
            yield line


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_resolve_modes_comma_separated() -> None:
    import argparse

    args = argparse.Namespace(modes="vanilla,hyde", rag_modes=None)
    assert br._resolve_modes(args) == ["vanilla", "hyde"]


def test_resolve_modes_legacy() -> None:
    import argparse

    args = argparse.Namespace(modes=None, rag_modes=["vanilla", "self_reflection"])
    assert br._resolve_modes(args) == ["vanilla", "self_reflection"]


def test_resolve_modes_default() -> None:
    import argparse

    args = argparse.Namespace(modes=None, rag_modes=None)
    assert br._resolve_modes(args) == br.RAG_MODES


def test_resolve_modes_invalid() -> None:
    import argparse

    args = argparse.Namespace(modes="vanilla,nonexistent", rag_modes=None)
    with pytest.raises(SystemExit):
        br._resolve_modes(args)


def test_stream_query_parses_tokens_and_citations() -> None:
    tokens = ["The", " answer", " is", " yes."]
    citations = [{"chunk_id": "c1", "snippet": "test", "filename": "doc.pdf"}]
    sse_lines = _make_sse_lines(tokens, citations, rag_mode="vanilla")

    fake_ctx = _FakeStreamCtx(sse_lines)
    mock_client = MagicMock()
    mock_client.stream.return_value = fake_ctx

    result = asyncio.run(
        br._stream_query(mock_client, "http://gw", "proj1", "Q?", "A", "token", None)
    )

    assert result["answer"] == "The answer is yes."
    assert result["citations"] == citations
    assert result["rag_mode"] == "vanilla"
    assert result["conversation_id"] == "conv-1"
    assert result["token_count"] == len(tokens)
    assert isinstance(result["latency_ms"], int)
    assert result["eval_result_id"] is None


def test_stream_query_empty_stream() -> None:
    sse_lines = ["data: [DONE]"]
    fake_ctx = _FakeStreamCtx(sse_lines)
    mock_client = MagicMock()
    mock_client.stream.return_value = fake_ctx

    result = asyncio.run(
        br._stream_query(mock_client, "http://gw", "proj1", "Q?", "A", "token", None)
    )

    assert result["answer"] == ""
    assert result["citations"] == []
    assert result["token_count"] == 0


def test_append_result_incremental(tmp_path: Path) -> None:
    output = tmp_path / "out.json"
    output.write_text("[]")

    br._append_result(output, {"rag_mode": "vanilla", "question": "Q1", "answer": "A1"})
    br._append_result(output, {"rag_mode": "hyde", "question": "Q2", "answer": "A2"})

    data = json.loads(output.read_text())
    assert len(data) == 2
    assert data[0]["rag_mode"] == "vanilla"
    assert data[1]["rag_mode"] == "hyde"


def test_dry_run_limit() -> None:
    """_DRY_RUN_LIMIT constant must be 10."""
    assert br._DRY_RUN_LIMIT == 10


def test_set_rag_mode_calls_patch() -> None:
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_client.patch.return_value = mock_resp

    br._set_rag_mode(mock_client, "http://gw", "proj1", "hyde", "tok")

    mock_client.patch.assert_called_once_with(
        "http://gw/admin/projects/proj1/settings",
        json={"rag_mode": "hyde"},
        headers={"Authorization": "Bearer tok"},
        timeout=30.0,
    )
    mock_resp.raise_for_status.assert_called_once()
