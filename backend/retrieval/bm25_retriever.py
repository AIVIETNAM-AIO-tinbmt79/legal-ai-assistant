from pathlib import Path

from indexing.bm25_indexer import BM25Indexer
from retrieval.retrieval_result import RetrievalResult


class BM25Retriever:
    """
    BM25 retriever using persistent BM25 index.
    """

    def __init__(
        self,
        index_path: str | Path = (
            "storage/bm25/bm25_index.pkl"
        ),
        top_k: int = 5,
    ):

        self.top_k = top_k

        self.indexer = BM25Indexer(
            index_path=index_path
        )

        self.indexer.load()

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
    ) -> list[RetrievalResult]:

        if not query or not query.strip():
            return []

        if not self.indexer.is_ready:
            raise RuntimeError(
                "BM25 index is not ready."
            )

        k = top_k or self.top_k

        query_tokens = (
            self.indexer.tokenize(query)
        )

        if not query_tokens:
            return []

        scores = self.indexer.bm25.get_scores(
            query_tokens
        )

        ranked_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True,
        )

        results = []

        for index in ranked_indices[:k]:

            results.append(
                RetrievalResult(
                    chunk=self.indexer.chunks[index],
                    score=float(scores[index]),
                    source="bm25",
                )
            )

        return results