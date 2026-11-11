from sentence_transformers import CrossEncoder

from config.settings import settings

from retrieval.retrieval_result import RetrievalResult
from reranking.base_reranker import BaseReranker


class CrossEncoderReranker(BaseReranker):
    """
    Cross-Encoder based reranker.
    """

    def __init__(
        self,
        model_name: str | None = None,
        max_length: int | None = None,
        segment_tokens: int | None = None,
        segment_overlap: int | None = None,
        device: str | None = None,
    ):

        # ==================================================
        # Configuration
        # ==================================================

        self.model_name = (
            model_name
            if model_name is not None
            else settings.RERANKER_MODEL
        )

        self.max_length = (
            max_length
            if max_length is not None
            else settings.RERANKER_MAX_LENGTH
        )

        self.segment_tokens = (
            segment_tokens
            if segment_tokens is not None
            else settings.RERANKER_SEGMENT_TOKENS
        )

        self.segment_overlap = (
            segment_overlap
            if segment_overlap is not None
            else settings.RERANKER_SEGMENT_OVERLAP
        )

        self.device = (
            device
            if device is not None
            else settings.RERANKER_DEVICE
        )

        # ==================================================
        # Validate
        # ==================================================

        if self.max_length <= 0:
            raise ValueError(
                "max_length must be > 0"
            )

        if self.segment_tokens <= 0:
            raise ValueError(
                "segment_tokens must be > 0"
            )

        if self.segment_overlap < 0:
            raise ValueError(
                "segment_overlap must be >= 0"
            )

        if (
            self.segment_overlap
            >= self.segment_tokens
        ):
            raise ValueError(
                "segment_overlap must be "
                "smaller than segment_tokens"
            )

        # ==================================================
        # Load Cross Encoder
        # ==================================================

        model_kwargs = {
            "max_length": self.max_length,
        }

        if self.device:
            model_kwargs["device"] = (
                self.device
            )

        self.model = CrossEncoder(
            self.model_name,
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
        top_k: int | None = None,
    ) -> list[RetrievalResult]:

        if not query or not query.strip():
            return []

        if not results:
            return []

        # ==============================================
        # Top K
        # ==============================================

        final_k = (
            top_k
            if top_k is not None
            else settings.RERANKER_TOP_K
        )

        if final_k <= 0:
            return []

        # ==============================================
        # Rerank
        # ==============================================

        reranked_results: list[
            RetrievalResult
        ] = []

        for result in results:

            score = self._score_chunk(
                query=query,
                text=result.chunk.text,
            )

            reranked_results.append(
                RetrievalResult(
                    chunk=result.chunk,
                    score=float(score),
                    source="reranker",
                )
            )

        # ==============================================
        # Sort
        # ==============================================

        reranked_results.sort(
            key=lambda result: result.score,
            reverse=True,
        )

        return reranked_results[:final_k]


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

        # ==============================================
        # Tokenize
        # ==============================================

        tokens = self.tokenizer.encode(
            text,
            add_special_tokens=False,
        )

        # ==============================================
        # Short Chunk
        # ==============================================

        if (
            len(tokens)
            <= self.segment_tokens
        ):

            score = self.model.predict(
                [(query, text)],
                show_progress_bar=False,
            )

            return float(score[0])

        # ==============================================
        # Long Chunk
        # ==============================================

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

        return self._aggregate_scores(
            scores
        )


    # ==================================================
    # Split Long Text
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

        segments: list[str] = []

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
    # Aggregate Scores
    # ==================================================

    @staticmethod
    def _aggregate_scores(
        scores,
    ) -> float:

        if scores is None:
            return float("-inf")

        if len(scores) == 0:
            return float("-inf")

        # Use maximum segment relevance.
        return float(
            max(
                float(score)
                for score in scores
            )
        )