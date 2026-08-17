from retrieval.retrieval_result import RetrievalResult


class ContextBuilder:
    """
    Build LLM context from reranked retrieval results.
    """

    def __init__(
        self,
        max_context_chars: int = 20000,
    ):
        self.max_context_chars = max_context_chars

    def build(
        self,
        results: list[RetrievalResult],
    ) -> str:

        if not results:
            return ""

        context_parts = []
        current_length = 0

        for index, result in enumerate(
            results,
            start=1,
        ):
            chunk = result.chunk

            text = chunk.text.strip()

            if not text:
                continue

            metadata = chunk.metadata

            article = getattr(
                metadata,
                "article",
                None,
            )

            section_title = getattr(
                metadata,
                "section_title",
                None,
            )

            header_parts = []

            if article:
                header_parts.append(
                    f"Điều {article}"
                )

            if section_title:
                header_parts.append(
                    section_title
                )

            if header_parts:
                header = " - ".join(
                    header_parts
                )
            else:
                header = f"Chunk {index}"

            part = (
                f"[{header}]\n"
                f"{text}"
            )

            # Check context limit
            if (
                current_length + len(part)
                > self.max_context_chars
            ):
                break

            context_parts.append(part)

            current_length += len(part)

        return "\n\n".join(
            context_parts
        )