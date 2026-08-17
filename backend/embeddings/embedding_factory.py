from embeddings.base_embedder import BaseEmbedder
from embeddings.sentence_transformer_embedder import (
    SentenceTransformerEmbedder,
)


class EmbeddingFactory:

    @staticmethod
    def create(
        provider: str = "sentence-transformer",
    ) -> BaseEmbedder:

        if provider == "sentence-transformer":
            return SentenceTransformerEmbedder()

        raise ValueError(
            f"Unsupported embedding provider: {provider}"
        )