from uuid import uuid4

from chunking.base_chunker import BaseChunker
from chunking.chunk_models import Chunk, ChunkMetadata
from chunking.length_splitter import LengthSplitter


class FallbackChunker(BaseChunker):
    """
    Fallback chunker for unstructured documents.

    Strategy:

        - Group paragraphs until max_chars is reached.
        - If a paragraph itself exceeds max_chars,
          split it using LengthSplitter.
        - Never discard document content.
    """

    def __init__(
        self,
        max_chars: int = 4000,
        overlap: int = 300,
    ):
        self.max_chars = max_chars
        self.overlap = overlap

        self.length_splitter = LengthSplitter(
            max_chars=max_chars,
            overlap=overlap,
        )

    def chunk(self, text: str) -> list[Chunk]:

        if not text or not text.strip():
            return []

        paragraphs = [
            paragraph.strip()
            for paragraph in text.split("\n\n")
            if paragraph.strip()
        ]

        chunks: list[Chunk] = []

        current_parts: list[str] = []
        current_length = 0

        def flush_chunk():

            nonlocal current_parts
            nonlocal current_length

            if not current_parts:
                return

            chunk_text = "\n\n".join(
                current_parts
            ).strip()

            chunks.append(
                Chunk(
                    id=str(uuid4()),
                    text=chunk_text,
                    metadata=ChunkMetadata(
                        chunk_type="fallback",
                    ),
                )
            )

            current_parts = []
            current_length = 0

        for paragraph in paragraphs:

            paragraph_length = len(paragraph)

            # ======================================
            # Paragraph itself is too large
            # ======================================

            if paragraph_length > self.max_chars:

                # Flush paragraphs accumulated before it.
                flush_chunk()

                # Create temporary chunk.
                temp_chunk = Chunk(
                    id=str(uuid4()),
                    text=paragraph,
                    metadata=ChunkMetadata(
                        chunk_type="fallback",
                    ),
                )

                # Split oversized paragraph.
                split_chunks = self.length_splitter.split(
                    temp_chunk
                )

                chunks.extend(split_chunks)

                continue

            # ======================================
            # Current chunk would exceed max_chars
            # ======================================

            if (
                current_parts
                and current_length + paragraph_length
                > self.max_chars
            ):
                flush_chunk()

            # ======================================
            # Add paragraph
            # ======================================

            current_parts.append(paragraph)

            current_length += paragraph_length

        # Flush remaining paragraphs.
        flush_chunk()

        return chunks