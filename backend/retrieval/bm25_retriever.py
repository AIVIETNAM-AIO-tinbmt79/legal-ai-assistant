from rank_bm25 import BM25Okapi
from underthesea import word_tokenize

from chunking.chunk_models import Chunk
from retrieval.base_retriever import BaseRetriever
from retrieval.retrieval_result import RetrievalResult


class BM25Retriever(BaseRetriever):
    """
    Keyword-based retriever using BM25.

    Vietnamese tokenization is handled by Underthesea.
    """

    def __init__(
        self,
        chunks: list[Chunk] | None = None,
    ):
        self.chunks: list[Chunk] = chunks or []

        self.tokenized_corpus: list[list[str]] = []

        self.bm25: BM25Okapi | None = None

        if self.chunks:
            self._build_index()

    # ==================================================
    # Build index
    # ==================================================

    def _build_index(self) -> None:
        """
        Build BM25 index from chunks.
        """

        self.tokenized_corpus = [
            self._tokenize(chunk.text)
            for chunk in self.chunks
        ]

        self.bm25 = BM25Okapi(
            self.tokenized_corpus
        )

    # ==================================================
    # Add chunks
    # ==================================================

    def add_chunks(
        self,
        chunks: list[Chunk],
    ) -> None:
        """
        Add chunks and rebuild the BM25 index.
        """

        if not chunks:
            return

        self.chunks.extend(chunks)

        self._build_index()

    # ==================================================
    # Retrieve
    # ==================================================

    def retrieve(
        self,
        query: str,
        top_k: int = 20,
    ) -> list[RetrievalResult]:

        if (
            not query
            or not query.strip()
            or self.bm25 is None
        ):
            return []

        tokenized_query = self._tokenize(query)

        scores = self.bm25.get_scores(
            tokenized_query
        )

        ranked_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True,
        )

        results: list[RetrievalResult] = []

        for index in ranked_indices[:top_k]:

            results.append(
                RetrievalResult(
                    chunk=self.chunks[index],
                    score=float(scores[index]),
                    source="bm25",
                )
            )

        return results

    # ==================================================
    # Tokenization
    # ==================================================

    @staticmethod
    def _tokenize(
        text: str,
    ) -> list[str]:
        """
        Vietnamese word segmentation using Underthesea.
        """

        if not text:
            return []

        tokenized_text = word_tokenize(
            text.lower(),
            format="text",
        )

        return tokenized_text.split()