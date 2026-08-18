from retrieval.vector_retriever import VectorRetriever
from retrieval.bm25_retriever import BM25Retriever
from retrieval.hybrid_retriever import HybridRetriever


class RetrieverFactory:

    @staticmethod
    def create(
        retriever_type: str = "hybrid",
        **kwargs,
    ):

        if retriever_type == "vector":

            return VectorRetriever(
                **kwargs
            )

        if retriever_type == "bm25":

            return BM25Retriever(
                **kwargs
            )

        if retriever_type == "hybrid":

            return HybridRetriever(
                **kwargs
            )

        raise ValueError(
            f"Unsupported retriever type: "
            f"{retriever_type}"
        )