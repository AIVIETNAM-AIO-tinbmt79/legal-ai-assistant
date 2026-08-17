from abc import ABC, abstractmethod

from retrieval.retrieval_result import RetrievalResult


class BaseRetriever(ABC):

    @abstractmethod
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[RetrievalResult]:
        """
        Retrieve relevant chunks for a query.
        """
        raise NotImplementedError