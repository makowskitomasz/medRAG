from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.strategies.base import BaseChunker


class RecursiveChunker(BaseChunker):
    def __init__(self, chunk_size: int = 512, overlap: int = 50) -> None:
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def split(self, text: str) -> list[str]:
        return [c for c in self._splitter.split_text(text) if c.strip()]
