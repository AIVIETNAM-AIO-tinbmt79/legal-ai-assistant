from abc import ABC, abstractmethod

from chunking.chunk_models import Chunk


class BaseChunker(ABC):
    """
    Base interface for all chunkers.
    """

    @abstractmethod
    def chunk(self, text: str) -> list[Chunk]:
        """
        Split document text into chunks.
        """
        raise NotImplementedError