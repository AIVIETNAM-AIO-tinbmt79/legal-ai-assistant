from config.settings import settings

from qdrant.vector_store_factory import (
    VectorStoreFactory,
)

from embeddings.embedding_factory import (
    EmbeddingFactory,
)

from retrieval.retrieval_result import (
    RetrievalResult,
)


class VectorRetriever:
    """
    Vector retriever using Qdrant.

    Supports contract-scoped retrieval.
    """

    def __init__(
        self,
        embedder=None,
        vector_store=None,
        top_k: int | None = None,
    ):

        self.top_k = (
            top_k
            if top_k is not None
            else settings.RETRIEVAL_TOP_K
        )

        self.embedder = (
            embedder
            if embedder is not None
            else EmbeddingFactory.create()
        )

        self.vector_store = (
            vector_store
            if vector_store is not None
            else VectorStoreFactory.create(
                dimension=self.embedder.dimension
            )
        )

    # ==================================================
    # Retrieve
    # ==================================================

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        contract_id: str | None = None,
    ) -> list[RetrievalResult]:

        if not query or not query.strip():
            return []

        k = (
            top_k
            if top_k is not None
            else self.top_k
        )

        # ==========================================
        # Embed query
        # ==========================================

        query_embedding = (
            self.embedder.embed_text(
                query
            )
        )

        if not query_embedding:
            return []

        # ==========================================
        # Qdrant Search
        # ==========================================

        points = (
            self.vector_store.search(
                query_embedding=query_embedding,
                top_k=k,
                contract_id=contract_id,
            )
        )

        # ==========================================
        # Convert results
        # ==========================================

        results: list[
            RetrievalResult
        ] = []

        for point in points:

            payload = (
                point.payload
                or {}
            )

            text = payload.get(
                "text",
                "",
            )

            metadata = payload.get(
                "metadata",
                {},
            )

            chunk = (
                self._build_chunk(
                    point_id=point.id,
                    text=text,
                    metadata=metadata,
                )
            )

            results.append(
                RetrievalResult(
                    chunk=chunk,
                    score=float(
                        point.score
                    ),
                    source="vector",
                )
            )

        return results

    # ==================================================
    # Build Chunk
    # ==================================================

    @staticmethod
    def _build_chunk(
        point_id,
        text: str,
        metadata: dict,
    ):

        from chunking.chunk_models import (
            Chunk,
        )

        return Chunk(
            id=str(point_id),
            text=text,
            metadata=metadata,
        )