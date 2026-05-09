from app.connectors.strategies.fixed import FixedChunker
from app.connectors.strategies.recursive import RecursiveChunker

TEXT = "word " * 300  # ~1500 chars


def test_fixed_chunker_splits():
    chunker = FixedChunker(chunk_size=100, overlap=10)
    chunks = chunker.split(TEXT)
    assert len(chunks) > 1
    assert all(len(c) <= 100 for c in chunks)


def test_fixed_chunker_empty():
    assert FixedChunker().split("") == []


def test_recursive_chunker_splits():
    chunker = RecursiveChunker(chunk_size=200, overlap=20)
    chunks = chunker.split(TEXT)
    assert len(chunks) > 1


def test_recursive_chunker_short_text():
    chunker = RecursiveChunker(chunk_size=500)
    chunks = chunker.split("short text")
    assert chunks == ["short text"]
