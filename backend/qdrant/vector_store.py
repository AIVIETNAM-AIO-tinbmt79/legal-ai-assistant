from typing import Any

from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from config.settings import settings

from chunking.chunk_models import Chunk

from qdrant.qdrant_client import (
    QdrantClientManager,
)


class QdrantVectorStore:
    """
    Vector store for legal document chunks.

    Supports contract-scoped retrieval.
    """

    def __init__(
        self,
        vector_size: int,
    ):

        # ==========================================
        # Qdrant Client
        # ==========================================

        self.client_manager = (
            QdrantClientManager()
        )

        self.client = (
            self.client_manager.get_client()
        )

        # ==========================================
        # Collection
        # ==========================================

        self.collection_name = (
            settings.QDRANT_COLLECTION
        )

        self.vector_size = vector_size

        self._ensure_collection()

    # ==================================================
    # Collection
    # ==================================================

    def _ensure_collection(
        self,
    ) -> None:

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
    # Add Chunks
    # ==================================================

    def add_chunks(
        self,
        chunks: list[Chunk],
        embeddings: list[list[float]],
    ) -> None:

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

                "metadata":
                    self._metadata_to_dict(
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
        contract_id: str | None = None,
    ):
        """
        Search similar vectors.

        If contract_id is provided, only chunks belonging
        to that contract are returned.
        """

        if not query_embedding:
            return []

        query_filter = None

        if contract_id:

            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="metadata.contract_id",
                        match=MatchValue(
                            value=contract_id
                        ),
                    )
                ]
            )

        results = (
            self.client.query_points(
                collection_name=self.collection_name,

                query=query_embedding,

                limit=top_k,

                query_filter=query_filter,

                with_payload=True,
            )
        )

        return results.points

    # ==================================================
    # Delete
    # ==================================================

    def delete_chunks(
        self,
        chunk_ids: list[str],
    ) -> None:

        if not chunk_ids:
            return

        self.client.delete(
            collection_name=self.collection_name,

            points_selector=chunk_ids,
        )

    # ==================================================
    # Collection Info
    # ==================================================

    def count(
        self,
    ) -> int:

        result = (
            self.client.count(
                collection_name=self.collection_name,
                exact=True,
            )
        )

        return result.count

    # ==================================================
    # Metadata
    # ==================================================

    @staticmethod
    def _metadata_to_dict(
        metadata: Any,
    ) -> dict:

        if hasattr(
            metadata,
            "model_dump",
        ):

            return metadata.model_dump()

        if hasattr(
            metadata,
            "dict",
        ):

            return metadata.dict()

        if hasattr(
            metadata,
            "__dict__",
        ):

            return metadata.__dict__

        return {}