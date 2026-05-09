from medrag_shared.models.project import ChunkingStrategy

from app.connectors.strategies.base import BaseChunker
from app.connectors.strategies.fixed import FixedChunker
from app.connectors.strategies.recursive import RecursiveChunker


def get_chunker(strategy: str) -> BaseChunker:
    if strategy == ChunkingStrategy.FIXED_512:
        return FixedChunker(chunk_size=512, overlap=50)
    return RecursiveChunker(chunk_size=512, overlap=50)
