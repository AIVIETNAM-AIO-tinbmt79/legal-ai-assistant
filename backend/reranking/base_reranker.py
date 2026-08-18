from abc import ABC, abstractmethod

from retrieval.retrieval_result import RetrievalResult


class BaseReranker(ABC):
    """
    Base interface for rerankers.
    """

    @abstractmethod
    def rerank(
        self,
        query: str,
        results: list[RetrievalResult],
        top_k: int = 5,
    ) -> list[RetrievalResult]:
        """
        Rerank retrieval results.
        """
        raise NotImplementedError