from typing import Any

from retrieval.base_retriever import BaseRetriever
from retrieval.bm25_retriever import BM25Retriever
from retrieval.hybrid_retriever import HybridRetriever
from retrieval.vector_retriever import VectorRetriever


class RetrieverFactory:

    @staticmethod
    def create(
        retriever_type: str,
        chunks: list[Any] | None = None,
        **kwargs,
    ) -> BaseRetriever:

        retriever_type = retriever_type.lower()

        if retriever_type == "vector":
            return VectorRetriever(
                **kwargs
            )

        if retriever_type == "bm25":
            return BM25Retriever(
                chunks=chunks
            )

        if retriever_type == "hybrid":
            return HybridRetriever(
                chunks=chunks,
                **kwargs,
            )

        raise ValueError(
            f"Unknown retriever type: {retriever_type}"
        )