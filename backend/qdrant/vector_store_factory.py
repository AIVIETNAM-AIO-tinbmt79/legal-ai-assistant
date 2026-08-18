from qdrant.vector_store import QdrantVectorStore


class VectorStoreFactory:

    @staticmethod
    def create(
        store_type: str = "qdrant",
        dimension: int | None = None,
    ):

        if store_type == "qdrant":

            if dimension is None:
                raise ValueError(
                    "dimension is required for Qdrant."
                )

            return QdrantVectorStore(
                vector_size=dimension
            )

        raise ValueError(
            f"Unsupported vector store type: "
            f"{store_type}"
        )