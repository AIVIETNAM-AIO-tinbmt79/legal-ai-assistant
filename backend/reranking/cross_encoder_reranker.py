from typing import Optional

from sentence_transformers import CrossEncoder

from retrieval.retrieval_result import RetrievalResult

from reranking.base_reranker import BaseReranker


class CrossEncoderReranker(BaseReranker):
    """
    Cross-Encoder based reranker.

    Flow:

        Query
          +
        Hybrid candidates
              ↓
        Cross Encoder
              ↓
        Relevance scores
              ↓
        Sort
              ↓
        Top K
    """

    def __init__(
        self,
        model_name: str = (
            "cross-encoder/ms-marco-MiniLM-L-6-v2"
        ),
        max_length: int = 1024,
        segment_tokens: int = 450,
        segment_overlap: int = 50,
        device: Optional[str] = None,
    ):

        self.model_name = model_name

        self.max_length = max_length

        self.segment_tokens = segment_tokens

        self.segment_overlap = segment_overlap

        # ==================================================
        # Validate
        # ==================================================

        if segment_tokens <= 0:
            raise ValueError(
                "segment_tokens must be > 0"
            )

        if segment_overlap < 0:
            raise ValueError(
                "segment_overlap must be >= 0"
            )

        if segment_overlap >= segment_tokens:
            raise ValueError(
                "segment_overlap must be "
                "smaller than segment_tokens"
            )

        # ==================================================
        # Load Cross Encoder
        # ==================================================

        model_kwargs = {
            "max_length": max_length,
        }

        if device is not None:
            model_kwargs["device"] = device

        self.model = CrossEncoder(
            model_name,
            **model_kwargs,
        )

        # ==================================================
        # Tokenizer
        # ==================================================

        self.tokenizer = self.model.tokenizer

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

        if top_k <= 0:
            return []

        reranked_results = []

        for result in results:

            score = self._score_chunk(
                query=query,
                text=result.chunk.text,
            )

            # --------------------------------------------------
            # Create new RetrievalResult
            # --------------------------------------------------

            reranked_result = RetrievalResult(
                chunk=result.chunk,
                score=float(score),
                source="reranker",
            )

            reranked_results.append(
                reranked_result
            )

        # ==================================================
        # Sort
        # ==================================================

        reranked_results.sort(
            key=lambda result: result.score,
            reverse=True,
        )

        # ==================================================
        # Top K
        # ==================================================

        return reranked_results[:top_k]

    # ==================================================
    # Score Chunk
    # ==================================================

    def _score_chunk(
        self,
        query: str,
        text: str,
    ) -> float:

        if not text or not text.strip():
            return float("-inf")

        # --------------------------------------------------
        # Tokenize chunk
        # --------------------------------------------------

        tokens = self.tokenizer.encode(
            text,
            add_special_tokens=False,
        )

        # --------------------------------------------------
        # Short chunk
        # --------------------------------------------------

        if len(tokens) <= self.segment_tokens:

            score = self.model.predict(
                [(query, text)],
                show_progress_bar=False,
            )

            return float(score[0])

        # --------------------------------------------------
        # Long chunk
        # --------------------------------------------------

        segments = self._split_tokens(
            text
        )

        if not segments:
            return float("-inf")

        pairs = [
            (query, segment)
            for segment in segments
        ]

        scores = self.model.predict(
            pairs,
            show_progress_bar=False,
        )

        # --------------------------------------------------
        # Aggregate
        # --------------------------------------------------

        return self._aggregate_scores(
            scores
        )

    # ==================================================
    # Split long text
    # ==================================================

    def _split_tokens(
        self,
        text: str,
    ) -> list[str]:

        token_ids = self.tokenizer.encode(
            text,
            add_special_tokens=False,
        )

        if not token_ids:
            return []

        step = (
            self.segment_tokens
            - self.segment_overlap
        )

        segments = []

        for start in range(
            0,
            len(token_ids),
            step,
        ):

            end = (
                start
                + self.segment_tokens
            )

            segment_ids = token_ids[
                start:end
            ]

            if not segment_ids:
                break

            segment = self.tokenizer.decode(
                segment_ids,
                skip_special_tokens=True,
            )

            if segment.strip():
                segments.append(
                    segment
                )

            if end >= len(token_ids):
                break

        return segments

    # ==================================================
    # Aggregate segment scores
    # ==================================================

    @staticmethod
    def _aggregate_scores(
        scores,
    ) -> float:

        if scores is None:
            return float("-inf")

        if len(scores) == 0:
            return float("-inf")

        # --------------------------------------------------
        # Use maximum segment relevance
        # --------------------------------------------------

        return float(
            max(float(score) for score in scores)
        )