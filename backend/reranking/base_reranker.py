from abc import ABC, abstractmethod

from retrieval.retrieval_result import RetrievalResult


class BaseReranker(ABC):

    @abstractmethod
    def rerank(
        self,
        query: str,
        results: list[RetrievalResult],
        top_k: int = 5,
    ) -> list[RetrievalResult]:
        """
        Rerank retrieved results according to their
        relevance to the query.
        """
        raise NotImplementedError