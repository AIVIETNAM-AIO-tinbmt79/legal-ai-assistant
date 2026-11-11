from pathlib import Path

from config.settings import settings

from indexing.bm25_indexer import BM25Indexer

from retrieval.retrieval_result import (
    RetrievalResult,
)


class BM25Retriever:
    """
    BM25 retriever using persistent shared BM25 index.

    Supports contract-scoped retrieval.
    """

    def __init__(
        self,
        index_path: str | Path | None = None,
        top_k: int | None = None,
    ):

        # ==========================================
        # Configuration
        # ==========================================

        self.index_path = (
            Path(index_path)
            if index_path is not None
            else settings.BM25_INDEX_PATH
        )

        self.top_k = (
            top_k
            if top_k is not None
            else settings.RETRIEVAL_TOP_K
        )

        # ==========================================
        # Indexer
        # ==========================================

        self.indexer = BM25Indexer(
            index_path=self.index_path
        )

        self.indexer.load()

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

        # ==========================================
        # Check index
        # ==========================================

        if not self.indexer.is_ready:
            raise RuntimeError(
                "BM25 index is not ready."
            )

        # ==========================================
        # Determine K
        # ==========================================

        k = (
            top_k
            if top_k is not None
            else self.top_k
        )

        # ==========================================
        # Tokenize query
        # ==========================================

        query_tokens = (
            self.indexer.tokenize(
                query
            )
        )

        if not query_tokens:
            return []

        # ==========================================
        # Calculate scores
        # ==========================================

        scores = (
            self.indexer
            .bm25
            .get_scores(
                query_tokens
            )
        )

        # ==========================================
        # Filter by contract
        # ==========================================

        candidate_indices = []

        for index, chunk in enumerate(
            self.indexer.chunks
        ):

            if contract_id is not None:

                chunk_contract_id = (
                    chunk.metadata.contract_id
                )

                if (
                    chunk_contract_id
                    != contract_id
                ):
                    continue

            candidate_indices.append(
                index
            )

        if not candidate_indices:
            return []

        # ==========================================
        # Rank only candidates
        # ==========================================

        ranked_indices = sorted(
            candidate_indices,
            key=lambda i: scores[i],
            reverse=True,
        )

        # ==========================================
        # Build results
        # ==========================================

        results: list[
            RetrievalResult
        ] = []

        for index in ranked_indices[:k]:

            results.append(
                RetrievalResult(
                    chunk=self.indexer.chunks[
                        index
                    ],
                    score=float(
                        scores[index]
                    ),
                    source="bm25",
                )
            )

        return results