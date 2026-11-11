from retrieval.retrieval_result import RetrievalResult


class ContextBuilder:
    """
    Build LLM context from reranked contract chunks.

    Đồng thời tạo danh sách sources để frontend
    có thể hiển thị nguồn của câu trả lời.
    """

    def __init__(
        self,
        max_context_chars: int = 20000,
    ):

        self.max_context_chars = (
            max_context_chars
        )

        self.sources: list[dict] = []


    # ========================================================
    # Metadata Helper
    # ========================================================

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

        # Pydantic object / normal object

        return getattr(
            metadata,
            key,
            None,
        )


    # ========================================================
    # Build
    # ========================================================

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

            if chunk is None:
                continue

            text = (
                chunk.text.strip()
                if chunk.text
                else ""
            )

            if not text:
                continue


            metadata = chunk.metadata


            # ------------------------------------------------
            # Metadata
            # ------------------------------------------------

            article = self._get_metadata(
                metadata,
                "article",
            )

            clause = self._get_metadata(
                metadata,
                "clause",
            )

            point = self._get_metadata(
                metadata,
                "point",
            )

            hierarchy_path = self._get_metadata(
                metadata,
                "hierarchy_path",
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


            # ------------------------------------------------
            # Header
            # ------------------------------------------------

            header_parts = []


            if article:

                header_parts.append(
                    f"Điều {article}"
                )


            if clause:

                header_parts.append(
                    f"Khoản {clause}"
                )


            if point:

                header_parts.append(
                    f"Điểm {point}"
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

                header = (
                    f"Chunk {index}"
                )


            # ------------------------------------------------
            # Context block
            # ------------------------------------------------

            part = (
                f"[{header}]\n"
                f"{text}"
            )


            # ------------------------------------------------
            # Context limit
            # ------------------------------------------------

            if (
                current_length
                + len(part)
                > self.max_context_chars
            ):

                break


            context_parts.append(
                part
            )

            current_length += len(part)


            # ------------------------------------------------
            # Source
            # ------------------------------------------------

            source = {

                "rank": index,

                "chunk_id": chunk.id,

                "article": article,

                "clause": clause,

                "point": point,

                "hierarchy_path": (
                    hierarchy_path
                ),

                "section_title": (
                    section_title
                ),

                "document_id": (
                    document_id
                ),

                "source_file": (
                    source_file
                ),

                "score": result.score,

                "retrieval_source": (
                    result.source
                ),

                "text": text,
            }


            self.sources.append(
                source
            )


        return "\n\n".join(
            context_parts
        )


    # ========================================================
    # Sources
    # ========================================================

    def get_sources(self) -> list[dict]:

        return self.sources