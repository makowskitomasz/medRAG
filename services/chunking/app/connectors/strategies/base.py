from abc import ABC, abstractmethod


class BaseChunker(ABC):
    @abstractmethod
    def split(self, text: str) -> list[str]:
        """Split text into chunks. Returns list of chunk strings."""
