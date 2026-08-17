from sentence_transformers import CrossEncoder

from retrieval.retrieval_result import RetrievalResult
from reranking.base_reranker import BaseReranker


class CrossEncoderReranker(BaseReranker):
    """
    Cross-Encoder reranker.

    Long legal chunks are temporarily split into smaller
    segments for reranking.

    The original legal Chunk is preserved.
    """

    def __init__(
        self,
        model_name: str,
        max_length: int = 1024,
        segment_tokens: int = 450,
        segment_overlap: int = 50,
    ):
        self.model_name = model_name
        self.max_length = max_length

        # Number of tokens used for each temporary segment.
        self.segment_tokens = segment_tokens
        self.segment_overlap = segment_overlap

        self.model = CrossEncoder(
            model_name,
            max_length=max_length,
        )

    # ==================================================
    # Rerank
    # ==================================================

    def rerank(
        self,
        query: str,
        results: list[RetrievalResult],
        top_k: int = 5,
    ) -> list[RetrievalResult]:

        if not query or not query.strip():
            return []

        if not results:
            return []

        reranked_results = []

        for result in results:

            chunk_text = result.chunk.text

            # ------------------------------------------
            # Short chunk
            # ------------------------------------------

            if self._count_tokens(chunk_text) <= self.segment_tokens:

                score = self._score(
                    query,
                    chunk_text,
                )

            # ------------------------------------------
            # Long chunk
            # ------------------------------------------

            else:

                segments = self._split_text(
                    chunk_text
                )

                segment_scores = []

                for segment in segments:

                    score = self._score(
                        query,
                        segment,
                    )

                    segment_scores.append(score)

                if not segment_scores:
                    continue

                # Most relevant part of the Article
                score = max(segment_scores)

            # ------------------------------------------
            # Preserve original Chunk
            # ------------------------------------------

            reranked_results.append(
                RetrievalResult(
                    chunk=result.chunk,
                    score=float(score),
                    source="reranker",
                    metadata={
                        "previous_score": result.score,
                        "previous_source": result.source,
                    },
                )
            )

        # ==========================================
        # Sort
        # ==========================================

        reranked_results.sort(
            key=lambda result: result.score,
            reverse=True,
        )

        return reranked_results[:top_k]

    # ==================================================
    # Score
    # ==================================================

    def _score(
        self,
        query: str,
        text: str,
    ) -> float:

        score = self.model.predict(
            [[query, text]],
            show_progress_bar=False,
        )

        return float(score[0])

    # ==================================================
    # Token count
    # ==================================================

    def _count_tokens(
        self,
        text: str,
    ) -> int:

        tokenizer = self.model.tokenizer

        tokens = tokenizer.encode(
            text,
            add_special_tokens=False,
        )

        return len(tokens)

    # ==================================================
    # Split long text
    # ==================================================

    def _split_text(
        self,
        text: str,
    ) -> list[str]:

        tokenizer = self.model.tokenizer

        token_ids = tokenizer.encode(
            text,
            add_special_tokens=False,
        )

        if not token_ids:
            return []

        segments = []

        step = (
            self.segment_tokens
            - self.segment_overlap
        )

        for start in range(
            0,
            len(token_ids),
            step,
        ):

            end = start + self.segment_tokens

            segment_ids = token_ids[start:end]

            segment = tokenizer.decode(
                segment_ids,
                skip_special_tokens=True,
            )

            if segment.strip():
                segments.append(segment)

            if end >= len(token_ids):
                break

        return segments