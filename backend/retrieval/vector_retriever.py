from qdrant.vector_store_factory import VectorStoreFactory

from embeddings.embedding_factory import EmbeddingFactory

from retrieval.retrieval_result import RetrievalResult


class VectorRetriever:
    """
    Vector retriever using Qdrant.

    Flow:

        Query
          ↓
        Embed query
          ↓
        Qdrant
          ↓
        Top K vectors
          ↓
        RetrievalResult
    """

    def __init__(
        self,
        embedder=None,
        vector_store=None,
        top_k: int = 5,
    ):
        self.top_k = top_k

        # ==================================================
        # Embedder
        # ==================================================

        self.embedder = (
            embedder
            or EmbeddingFactory.create()
        )

        # ==================================================
        # Vector Store
        # ==================================================

        self.vector_store = (
            vector_store
            or VectorStoreFactory.create(
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
    ) -> list[RetrievalResult]:

        if not query or not query.strip():
            return []

        k = top_k or self.top_k

        # --------------------------------------------------
        # 1. Embed query
        # --------------------------------------------------

        query_embedding = self.embedder.embed_text(
            query
        )

        # --------------------------------------------------
        # 2. Qdrant search
        # --------------------------------------------------

        points = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=k,
        )

        # --------------------------------------------------
        # 3. Convert Qdrant results
        # --------------------------------------------------

        results = []

        for point in points:

            payload = point.payload or {}

            text = payload.get(
                "text",
                "",
            )

            metadata = payload.get(
                "metadata",
                {},
            )

            # --------------------------------------------------
            # Reconstruct chunk
            # --------------------------------------------------

            chunk = self._build_chunk(
                point_id=point.id,
                text=text,
                metadata=metadata,
            )

            results.append(
                RetrievalResult(
                    chunk=chunk,
                    score=float(point.score),
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
        """
        Reconstruct Chunk from Qdrant payload.
        """

        from chunking.chunk_models import Chunk

        return Chunk(
            id=str(point_id),
            text=text,
            metadata=metadata,
        )