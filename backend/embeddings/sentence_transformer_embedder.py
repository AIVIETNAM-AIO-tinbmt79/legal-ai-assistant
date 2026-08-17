from sentence_transformers import SentenceTransformer

from embeddings.base_embedder import BaseEmbedder
from embeddings.embedding_config import (
    EMBEDDING_MODEL,
    EMBEDDING_DEVICE,
)


class SentenceTransformerEmbedder(BaseEmbedder):
    """
    Embedding implementation using SentenceTransformer.
    """

    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,
    ):
        self.model_name = (
            model_name
            or EMBEDDING_MODEL
        )

        self.device = (
            device
            or EMBEDDING_DEVICE
        )

        self.model = SentenceTransformer(
            self.model_name,
            device=self.device,
        )

    @property
    def dimension(self) -> int:
        return self.model.get_sentence_embedding_dimension()

    def embed_text(
        self,
        text: str,
    ) -> list[float]:

        if not text or not text.strip():
            return []

        vector = self.model.encode(
            text,
            normalize_embeddings=True,
        )

        return vector.tolist()

    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:

        if not texts:
            return []

        vectors = self.model.encode(
            texts,
            normalize_embeddings=True,
        )

        return vectors.tolist()
    