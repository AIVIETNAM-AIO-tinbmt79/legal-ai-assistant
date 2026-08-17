from chunking.chunk_models import Chunk

from retrieval.base_retriever import BaseRetriever
from retrieval.bm25_retriever import BM25Retriever
from retrieval.retrieval_result import RetrievalResult
from retrieval.vector_retriever import VectorRetriever


class HybridRetriever(BaseRetriever):
    """
    Hybrid retriever.

    Combines:

        Dense / Semantic Retrieval
        +
        BM25 Retrieval

    Fusion:
        Weighted Reciprocal Rank Fusion (RRF)

    Default:
        Semantic = 0.7
        BM25     = 0.3
    """

    def __init__(
        self,
        chunks: list[Chunk] | None = None,
        top_k: int = 20,
        retrieval_k: int = 20,
        rrf_k: int = 60,
        semantic_weight: float = 0.7,
        bm25_weight: float = 0.3,
    ):
        self.top_k = top_k
        self.retrieval_k = retrieval_k
        self.rrf_k = rrf_k

        self.semantic_weight = semantic_weight
        self.bm25_weight = bm25_weight

        # ==========================================
        # Validate weights
        # ==========================================

        if semantic_weight < 0:
            raise ValueError(
                "semantic_weight must be >= 0"
            )

        if bm25_weight < 0:
            raise ValueError(
                "bm25_weight must be >= 0"
            )

        if semantic_weight + bm25_weight == 0:
            raise ValueError(
                "At least one weight must be > 0"
            )

        # ==========================================
        # Retrievers
        # ==========================================

        self.vector_retriever = VectorRetriever(
            top_k=retrieval_k
        )

        self.bm25_retriever = BM25Retriever(
            chunks=chunks
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

        final_top_k = top_k or self.top_k

        # ==========================================
        # 1. Semantic retrieval
        # ==========================================

        vector_results = (
            self.vector_retriever.retrieve(
                query=query,
                top_k=self.retrieval_k,
            )
        )

        # ==========================================
        # 2. BM25 retrieval
        # ==========================================

        bm25_results = (
            self.bm25_retriever.retrieve(
                query=query,
                top_k=self.retrieval_k,
            )
        )

        # ==========================================
        # 3. Weighted RRF
        # ==========================================

        scores: dict[str, float] = {}

        chunks: dict[str, Chunk] = {}

        # ------------------------------------------
        # Semantic
        # ------------------------------------------

        for rank, result in enumerate(
            vector_results,
            start=1,
        ):

            chunk_id = result.chunk.id

            rrf_score = (
                self.semantic_weight
                / (self.rrf_k + rank)
            )

            scores[chunk_id] = (
                scores.get(chunk_id, 0.0)
                + rrf_score
            )

            chunks[chunk_id] = result.chunk

        # ------------------------------------------
        # BM25
        # ------------------------------------------

        for rank, result in enumerate(
            bm25_results,
            start=1,
        ):

            chunk_id = result.chunk.id

            rrf_score = (
                self.bm25_weight
                / (self.rrf_k + rank)
            )

            scores[chunk_id] = (
                scores.get(chunk_id, 0.0)
                + rrf_score
            )

            chunks[chunk_id] = result.chunk

        # ==========================================
        # 4. Sort
        # ==========================================

        ranked = sorted(
            scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        # ==========================================
        # 5. Return
        # ==========================================

        results: list[RetrievalResult] = []

        for chunk_id, score in ranked[:final_top_k]:

            results.append(
                RetrievalResult(
                    chunk=chunks[chunk_id],
                    score=float(score),
                    source="hybrid",
                )
            )

        return results