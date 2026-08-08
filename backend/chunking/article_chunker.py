from uuid import uuid4

from chunking.base_chunker import BaseChunker
from chunking.chunk_models import Chunk, ChunkMetadata
from chunking.legal_patterns import match_article


class ArticleChunker(BaseChunker):
    """
    Main chunking strategy for article-based legal documents.

    Strategy:

        - Content before the first Article -> Preamble chunk
        - 1 Article -> 1 Chunk
        - Clauses and points remain inside the article text
        - Content after the last Article remains inside the last Article
    """

    def chunk(self, text: str) -> list[Chunk]:

        if not text or not text.strip():
            return []

        lines = text.splitlines()

        chunks: list[Chunk] = []

        current_article: str | None = None
        current_title: str | None = None
        current_lines: list[str] = []

        def flush_chunk():

            nonlocal current_lines
            nonlocal current_article
            nonlocal current_title

            chunk_text = "\n".join(current_lines).strip()

            if not chunk_text:
                current_lines = []
                return

            # Before the first Article
            if current_article is None:
                chunk_type = "preamble"
            else:
                chunk_type = "article"

            metadata = ChunkMetadata(
                article=current_article,
                section_title=current_title,
                chunk_type=chunk_type,
            )

            chunks.append(
                Chunk(
                    id=str(uuid4()),
                    text=chunk_text,
                    metadata=metadata,
                )
            )

            current_lines = []

        # ==========================================
        # Process lines
        # ==========================================

        for line in lines:

            line = line.strip()

            if not line:
                continue

            article_match = match_article(line)

            # --------------------------------------
            # Found a new Article
            # --------------------------------------

            if article_match:

                # Save previous content.
                #
                # This can be:
                # - preamble
                # - previous article
                flush_chunk()

                current_article = article_match.group(1)

                title = article_match.group(2)

                current_title = (
                    title.strip()
                    if title
                    else None
                )

                current_lines = [line]

                continue

            # --------------------------------------
            # Normal content
            # --------------------------------------

            current_lines.append(line)

        # ==========================================
        # Flush remaining content
        # ==========================================

        flush_chunk()

        return chunks