from typing import Any

from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)

from chunking.chunk_models import Chunk

from qdrant.qdrant_client import QdrantClientManager
from qdrant.qdrant_config import QDRANT_COLLECTION


class QdrantVectorStore:
    """
    Vector store for legal document chunks.

    Responsibilities:
        - Manage Qdrant collection
        - Store chunks + embeddings
        - Search similar vectors
        - Delete chunks
    """

    def __init__(
        self,
        vector_size: int,
    ):

        self.client_manager = QdrantClientManager()

        self.client = (
            self.client_manager.get_client()
        )

        self.collection_name = (
            QDRANT_COLLECTION
        )

        self.vector_size = vector_size

        self._ensure_collection()

    # ==================================================
    # Collection
    # ==================================================

    def _ensure_collection(self) -> None:
        """
        Create collection if it does not exist.
        """

        collections = (
            self.client.get_collections()
        )

        exists = any(
            collection.name
            == self.collection_name
            for collection
            in collections.collections
        )

        if exists:
            return

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.vector_size,
                distance=Distance.COSINE,
            ),
        )

    # ==================================================
    # Add chunks
    # ==================================================

    def add_chunks(
        self,
        chunks: list[Chunk],
        embeddings: list[list[float]],
    ) -> None:
        """
        Store chunks and their embeddings.
        """

        if not chunks:
            return

        if len(chunks) != len(embeddings):
            raise ValueError(
                "Number of chunks and embeddings "
                "must be the same."
            )

        points: list[PointStruct] = []

        for chunk, embedding in zip(
            chunks,
            embeddings,
        ):

            payload = {
                "text": chunk.text,
                "metadata": self._metadata_to_dict(
                    chunk.metadata
                ),
            }

            points.append(
                PointStruct(
                    id=chunk.id,
                    vector=embedding,
                    payload=payload,
                )
            )

        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )

    # ==================================================
    # Search
    # ==================================================

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
    ):
        """
        Search for the most similar chunks.
        """

        if not query_embedding:
            return []

        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_embedding,
            limit=top_k,
            with_payload=True,
        )

        return results.points

    # ==================================================
    # Delete
    # ==================================================

    def delete_chunks(
        self,
        chunk_ids: list[str],
    ) -> None:
        """
        Delete chunks from Qdrant.
        """

        if not chunk_ids:
            return

        self.client.delete(
            collection_name=self.collection_name,
            points_selector=chunk_ids,
        )

    # ==================================================
    # Collection info
    # ==================================================

    def count(self) -> int:
        """
        Return number of stored vectors.
        """

        result = self.client.count(
            collection_name=self.collection_name,
            exact=True,
        )

        return result.count

    # ==================================================
    # Metadata
    # ==================================================

    @staticmethod
    def _metadata_to_dict(
        metadata: Any,
    ) -> dict:
        """
        Convert ChunkMetadata into a dictionary.
        """

        if hasattr(metadata, "model_dump"):
            return metadata.model_dump()

        if hasattr(metadata, "dict"):
            return metadata.dict()

        if hasattr(metadata, "__dict__"):
            return metadata.__dict__

        return {}