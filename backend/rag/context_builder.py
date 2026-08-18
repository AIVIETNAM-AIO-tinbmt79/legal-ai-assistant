from retrieval.retrieval_result import RetrievalResult


class ContextBuilder:
    """
    Build LLM context from reranked retrieval results.

    Besides the context string, this builder also keeps
    source information for citation.
    """

    def __init__(
        self,
        max_context_chars: int = 20000,
    ):
        self.max_context_chars = max_context_chars

        self.sources = []

    # ==================================================
    # Get metadata value
    # ==================================================

    @staticmethod
    def _get_metadata(
        metadata,
        key: str,
    ):

        if metadata is None:
            return None

        # Dictionary
        if isinstance(
            metadata,
            dict,
        ):
            return metadata.get(key)

        # Object
        return getattr(
            metadata,
            key,
            None,
        )

    # ==================================================
    # Build context
    # ==================================================

    def build(
        self,
        results: list[RetrievalResult],
    ) -> str:

        self.sources = []

        if not results:
            return ""

        context_parts = []
        current_length = 0

        for index, result in enumerate(
            results,
            start=1,
        ):

            chunk = result.chunk

            text = (
                chunk.text.strip()
                if chunk.text
                else ""
            )

            if not text:
                continue

            metadata = chunk.metadata

            article = self._get_metadata(
                metadata,
                "article",
            )

            section_title = self._get_metadata(
                metadata,
                "section_title",
            )

            document_id = self._get_metadata(
                metadata,
                "document_id",
            )

            source_file = self._get_metadata(
                metadata,
                "source_file",
            )

            # ==========================================
            # Build source label
            # ==========================================

            header_parts = []

            if article:
                header_parts.append(
                    f"Điều {article}"
                )

            if section_title:
                header_parts.append(
                    str(section_title)
                )

            if header_parts:

                header = " - ".join(
                    header_parts
                )

            else:

                header = f"Chunk {index}"

            # ==========================================
            # Build context
            # ==========================================

            part = (
                f"[{header}]\n"
                f"{text}"
            )

            # ==========================================
            # Context limit
            # ==========================================

            if (
                current_length + len(part)
                > self.max_context_chars
            ):
                break

            context_parts.append(
                part
            )

            current_length += len(part)

            # ==========================================
            # Save source
            # ==========================================

            source = {
                "rank": index,
                "chunk_id": chunk.id,
                "article": article,
                "section_title": section_title,
                "document_id": document_id,
                "source_file": source_file,
                "score": result.score,
                "text": text,
            }

            self.sources.append(
                source
            )

        return "\n\n".join(
            context_parts
        )

    # ==================================================
    # Get sources
    # ==================================================

    def get_sources(self):
        return self.sources