from typing import Optional

from retrieval.vector_retriever import VectorRetriever
from retrieval.bm25_retriever import BM25Retriever
from retrieval.retrieval_result import RetrievalResult


class HybridRetriever:
    """
    Hybrid retriever combining:

        Vector Search + BM25

    Score:

        hybrid_score =
            semantic_weight * normalized_vector_score
            +
            bm25_weight * normalized_bm25_score

    Default:

        semantic_weight = 0.7
        bm25_weight = 0.3
    """

    def __init__(
        self,
        vector_retriever: Optional[VectorRetriever] = None,
        bm25_retriever: Optional[BM25Retriever] = None,
        top_k: int = 5,
        retrieval_k: int = 20,
        semantic_weight: float = 0.7,
        bm25_weight: float = 0.3,
    ):

        # ==================================================
        # Validate weights
        # ==================================================

        if semantic_weight < 0:
            raise ValueError(
                "semantic_weight must be >= 0"
            )

        if bm25_weight < 0:
            raise ValueError(
                "bm25_weight must be >= 0"
            )

        total_weight = (
            semantic_weight
            + bm25_weight
        )

        if total_weight <= 0:
            raise ValueError(
                "At least one retrieval weight "
                "must be greater than 0."
            )

        # Normalize weights
        self.semantic_weight = (
            semantic_weight / total_weight
        )

        self.bm25_weight = (
            bm25_weight / total_weight
        )

        # ==================================================
        # Configuration
        # ==================================================

        self.top_k = top_k
        self.retrieval_k = retrieval_k

        # ==================================================
        # Retrievers
        # ==================================================

        self.vector_retriever = (
            vector_retriever
            or VectorRetriever(
                top_k=retrieval_k
            )
        )

        self.bm25_retriever = (
            bm25_retriever
            or BM25Retriever(
                top_k=retrieval_k
            )
        )

    # ==================================================
    # Retrieve
    # ==================================================

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
    ) -> list[RetrievalResult]:

        if not query or not query.strip():
            return []

        final_k = top_k or self.top_k

        # ==================================================
        # 1. Vector Retrieval
        # ==================================================

        vector_results = (
            self.vector_retriever.retrieve(
                query=query,
                top_k=self.retrieval_k,
            )
        )

        # ==================================================
        # 2. BM25 Retrieval
        # ==================================================

        bm25_results = (
            self.bm25_retriever.retrieve(
                query=query,
                top_k=self.retrieval_k,
            )
        )

        # ==================================================
        # 3. Normalize scores
        # ==================================================

        vector_scores = {
            result.chunk.id: result.score
            for result in vector_results
        }

        bm25_scores = {
            result.chunk.id: result.score
            for result in bm25_results
        }

        normalized_vector = self._normalize_scores(
            vector_scores
        )

        normalized_bm25 = self._normalize_scores(
            bm25_scores
        )

        # ==================================================
        # 4. Merge candidates
        # ==================================================

        candidate_ids = set(
            normalized_vector.keys()
        ) | set(
            normalized_bm25.keys()
        )

        # Keep chunk references
        chunks = {}

        for result in vector_results:
            chunks[result.chunk.id] = result.chunk

        for result in bm25_results:
            chunks[result.chunk.id] = result.chunk

        # ==================================================
        # 5. Hybrid scoring
        # ==================================================

        hybrid_results = []

        for chunk_id in candidate_ids:

            vector_score = normalized_vector.get(
                chunk_id,
                0.0,
            )

            bm25_score = normalized_bm25.get(
                chunk_id,
                0.0,
            )

            hybrid_score = (
                self.semantic_weight
                * vector_score
                +
                self.bm25_weight
                * bm25_score
            )

            hybrid_results.append(
                RetrievalResult(
                    chunk=chunks[chunk_id],
                    score=float(hybrid_score),
                    source="hybrid",
                )
            )

        # ==================================================
        # 6. Sort
        # ==================================================

        hybrid_results.sort(
            key=lambda result: result.score,
            reverse=True,
        )

        # ==================================================
        # 7. Top K
        # ==================================================

        return hybrid_results[:final_k]

    # ==================================================
    # Score normalization
    # ==================================================

    @staticmethod
    def _normalize_scores(
        scores: dict[str, float],
    ) -> dict[str, float]:

        if not scores:
            return {}

        values = list(
            scores.values()
        )

        min_score = min(values)
        max_score = max(values)

        # ----------------------------------------------
        # All scores are equal
        # ----------------------------------------------

        if max_score == min_score:

            return {
                chunk_id: 1.0
                for chunk_id in scores
            }

        # ----------------------------------------------
        # Min-Max normalization
        # ----------------------------------------------

        return {
            chunk_id: (
                (score - min_score)
                / (max_score - min_score)
            )
            for chunk_id, score
            in scores.items()
        }