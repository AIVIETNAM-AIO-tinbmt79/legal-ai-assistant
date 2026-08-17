from abc import ABC, abstractmethod


class BaseEmbedder(ABC):

    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        """
        Convert a single text into an embedding vector.
        """
        pass

    @abstractmethod
    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """
        Convert multiple texts into embedding vectors.
        """
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """
        Return embedding vector dimension.
        """
        pass