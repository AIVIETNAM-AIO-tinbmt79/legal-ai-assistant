from chunking.chunk_models import Chunk, ChunkMetadata

from embeddings.embedding_factory import EmbeddingFactory
from retrieval.base_retriever import BaseRetriever
from retrieval.retrieval_result import RetrievalResult
from vector_store.vector_store_factory import VectorStoreFactory


class VectorRetriever(BaseRetriever):
    """
    Semantic retriever using embeddings + Qdrant.
    """

    def __init__(
        self,
        top_k: int = 20,
    ):
        self.top_k = top_k

        # ==========================================
        # Embedding
        # ==========================================

        self.embedder = EmbeddingFactory.create()

        # ==========================================
        # Vector store
        # ==========================================

        self.vector_store = VectorStoreFactory.create(
            vector_size=self.embedder.dimension
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

        # ==========================================
        # Embed query
        # ==========================================

        query_embedding = self.embedder.embed_text(
            query
        )

        # ==========================================
        # Search Qdrant
        # ==========================================

        results = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=k,
        )

        # ==========================================
        # Convert Qdrant results
        # ==========================================

        retrieval_results: list[RetrievalResult] = []

        for result in results:

            payload = result.payload or {}

            text = payload.get("text")

            if not text:
                continue

            metadata_dict = payload.get(
                "metadata",
                {},
            )

            chunk = Chunk(
                id=str(result.id),
                text=text,
                metadata=ChunkMetadata(
                    **metadata_dict
                ),
            )

            retrieval_results.append(
                RetrievalResult(
                    chunk=chunk,
                    score=float(result.score),
                    source="vector",
                )
            )

        return retrieval_results