from reranking.cross_encoder_reranker import (
    CrossEncoderReranker,
)


class RerankerFactory:

    @staticmethod
    def create(
        reranker_type: str = "cross_encoder",
        **kwargs,
    ):

        if reranker_type == "cross_encoder":

            return CrossEncoderReranker(
                **kwargs
            )

        raise ValueError(
            f"Unsupported reranker type: "
            f"{reranker_type}"
        )
