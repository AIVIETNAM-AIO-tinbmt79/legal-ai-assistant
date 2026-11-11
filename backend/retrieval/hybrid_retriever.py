from retrieval.vector_retriever import (
    VectorRetriever,
)

from retrieval.bm25_retriever import (
    BM25Retriever,
)

from retrieval.retrieval_result import (
    RetrievalResult,
)

from config.settings import settings


class HybridRetriever:
    """
    Hybrid retriever combining:

        Vector Search + BM25

    Score:

        hybrid_score =
            semantic_weight
            * normalized_vector_score
            +
            bm25_weight
            * normalized_bm25_score
    """

    def __init__(
        self,
        vector_retriever: VectorRetriever | None = None,
        bm25_retriever: BM25Retriever | None = None,
        top_k: int | None = None,
        retrieval_k: int | None = None,
        semantic_weight: float | None = None,
        bm25_weight: float | None = None,
    ):

        # ==================================================
        # Configuration
        # ==================================================

        self.top_k = (
            top_k
            if top_k is not None
            else settings.RETRIEVAL_TOP_K
        )

        self.retrieval_k = (
            retrieval_k
            if retrieval_k is not None
            else settings.RETRIEVAL_TOP_K
        )

        self.semantic_weight = (
            semantic_weight
            if semantic_weight is not None
            else settings.SEMANTIC_WEIGHT
        )

        self.bm25_weight = (
            bm25_weight
            if bm25_weight is not None
            else settings.BM25_WEIGHT
        )

        # ==================================================
        # Validate K
        # ==================================================

        if self.top_k <= 0:
            raise ValueError(
                "top_k must be greater than 0."
            )

        if self.retrieval_k <= 0:
            raise ValueError(
                "retrieval_k must be greater than 0."
            )

        # ==================================================
        # Validate weights
        # ==================================================

        if self.semantic_weight < 0:
            raise ValueError(
                "semantic_weight must be >= 0"
            )

        if self.bm25_weight < 0:
            raise ValueError(
                "bm25_weight must be >= 0"
            )

        total_weight = (
            self.semantic_weight
            + self.bm25_weight
        )

        if total_weight <= 0:
            raise ValueError(
                "At least one retrieval weight "
                "must be greater than 0."
            )

        # Normalize weights

        self.semantic_weight /= total_weight
        self.bm25_weight /= total_weight

        # ==================================================
        # Retrievers
        # ==================================================

        self.vector_retriever = (
            vector_retriever
            if vector_retriever is not None
            else VectorRetriever(
                top_k=self.retrieval_k
            )
        )

        self.bm25_retriever = (
            bm25_retriever
            if bm25_retriever is not None
            else BM25Retriever(
                top_k=self.retrieval_k
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

        # ==================================================
        # Final Top K
        # ==================================================

        final_k = (
            top_k
            if top_k is not None
            else self.top_k
        )

        if final_k <= 0:
            return []

        # ==================================================
        # 1. Vector Retrieval
        # ==================================================

        vector_results = (
            self.vector_retriever.retrieve(
                query=query,
                top_k=self.retrieval_k,
                contract_id=contract_id,
            )
        )

        # ==================================================
        # 2. BM25 Retrieval
        # ==================================================

        bm25_results = (
            self.bm25_retriever.retrieve(
                query=query,
                top_k=self.retrieval_k,
                contract_id=contract_id,
            )
        )

        # ==================================================
        # 3. Normalize Scores
        # ==================================================

        vector_scores = {
            result.chunk.id: result.score
            for result in vector_results
        }

        bm25_scores = {
            result.chunk.id: result.score
            for result in bm25_results
        }

        normalized_vector = (
            self._normalize_scores(
                vector_scores
            )
        )

        normalized_bm25 = (
            self._normalize_scores(
                bm25_scores
            )
        )

        # ==================================================
        # 4. Merge Candidates
        # ==================================================

        candidate_ids = (
            set(normalized_vector.keys())
            |
            set(normalized_bm25.keys())
        )

        if not candidate_ids:
            return []

        # ==================================================
        # 5. Keep Chunk References
        # ==================================================

        chunks = {}

        for result in vector_results:
            chunks[result.chunk.id] = result.chunk

        for result in bm25_results:
            chunks[result.chunk.id] = result.chunk

        # ==================================================
        # 6. Hybrid Scoring
        # ==================================================

        hybrid_results = []

        for chunk_id in candidate_ids:

            vector_score = (
                normalized_vector.get(
                    chunk_id,
                    0.0,
                )
            )

            bm25_score = (
                normalized_bm25.get(
                    chunk_id,
                    0.0,
                )
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
        # 7. Sort
        # ==================================================

        hybrid_results.sort(
            key=lambda result: result.score,
            reverse=True,
        )

        return hybrid_results[:final_k]

    # ==================================================
    # Normalize Scores
    # ==================================================

    @staticmethod
    def _normalize_scores(
        scores: dict[str, float],
    ) -> dict[str, float]:

        if not scores:
            return {}

        values = list(scores.values())

        min_score = min(values)
        max_score = max(values)

        # --------------------------------------------------
        # All scores are identical
        # --------------------------------------------------

        if max_score == min_score:

            return {
                chunk_id: 1.0
                for chunk_id in scores
            }

        # --------------------------------------------------
        # Min-Max normalization
        # --------------------------------------------------

        denominator = max_score - min_score

        return {
            chunk_id: (
                (score - min_score)
                / denominator
            )
            for chunk_id, score in scores.items()
        }