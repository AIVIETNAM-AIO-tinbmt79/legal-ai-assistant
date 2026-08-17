from vector_store.vector_store import QdrantVectorStore


class VectorStoreFactory:
    """
    Factory for creating vector store implementations.
    """

    @staticmethod
    def create(
        provider: str = "qdrant",
        vector_size: int | None = None,
    ) -> QdrantVectorStore:

        if vector_size is None:
            raise ValueError(
                "vector_size must be provided."
            )

        if provider == "qdrant":
            return QdrantVectorStore(
                vector_size=vector_size
            )

        raise ValueError(
            f"Unsupported vector store provider: {provider}"
        )