import os

from reranking.base_reranker import BaseReranker
from reranking.cross_encoder_reranker import CrossEncoderReranker


class RerankerFactory:

    @staticmethod
    def create(
        reranker_type: str = "cross_encoder",
        **kwargs,
    ) -> BaseReranker:

        reranker_type = reranker_type.lower()

        if reranker_type == "cross_encoder":

            model_name = kwargs.get(
                "model_name",
                os.getenv("RERANKER_MODEL"),
            )

            if not model_name:
                raise ValueError(
                    "RERANKER_MODEL is not configured."
                )

            max_length = kwargs.get(
                "max_length",
                1024,
            )

            segment_tokens = kwargs.get(
                "segment_tokens",
                450,
            )

            segment_overlap = kwargs.get(
                "segment_overlap",
                50,
            )

            return CrossEncoderReranker(
                model_name=model_name,
                max_length=max_length,
                segment_tokens=segment_tokens,
                segment_overlap=segment_overlap,
            )

        raise ValueError(
            f"Unknown reranker type: {reranker_type}"
        )