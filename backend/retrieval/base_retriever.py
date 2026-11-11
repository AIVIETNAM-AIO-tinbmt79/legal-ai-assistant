from abc import ABC, abstractmethod

from retrieval.retrieval_result import RetrievalResult


class BaseRetriever(ABC):
    """
    Base interface for all retrievers.
    """

    @abstractmethod
    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        contract_id: str | None = None,
    ) -> list[RetrievalResult]:
        """
        Retrieve relevant chunks for a query.

        Args:
            query:
                User query.

            top_k:
                Number of results.

            contract_id:
                Restrict retrieval to one contract.
        """

        raise NotImplementedError   