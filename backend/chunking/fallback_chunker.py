from uuid import uuid4

from config.settings import settings

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
        max_chars: int | None = None,
        overlap: int | None = None,
    ):

        # ======================================
        # Load from settings if not provided
        # ======================================

        self.max_chars = (
            max_chars
            if max_chars is not None
            else settings.CHUNK_MAX_CHARS
        )

        self.overlap = (
            overlap
            if overlap is not None
            else settings.CHUNK_OVERLAP
        )

        # ======================================
        # Validation
        # ======================================

        if self.max_chars <= 0:

            raise ValueError(
                "max_chars must be greater than 0."
            )

        if self.overlap < 0:

            raise ValueError(
                "overlap cannot be negative."
            )

        if self.overlap >= self.max_chars:

            raise ValueError(
                "overlap must be smaller than max_chars."
            )

        # ======================================
        # Length Splitter
        # ======================================

        self.length_splitter = LengthSplitter(
            max_chars=self.max_chars,
            overlap=self.overlap,
        )


    # ==================================================
    # Chunk
    # ==================================================

    def chunk(
        self,
        text: str,
    ) -> list[Chunk]:

        if not text or not text.strip():

            return []


        # ======================================
        # Split paragraphs
        # ======================================

        paragraphs = [

            paragraph.strip()

            for paragraph in text.split("\n\n")

            if paragraph.strip()

        ]


        chunks: list[Chunk] = []

        current_parts: list[str] = []

        current_length = 0


        # ======================================
        # Flush Chunk
        # ======================================

        def flush_chunk():

            nonlocal current_parts
            nonlocal current_length

            if not current_parts:

                return


            chunk_text = "\n\n".join(
                current_parts
            ).strip()


            if not chunk_text:

                return


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


        # ======================================
        # Process Paragraphs
        # ======================================

        for paragraph in paragraphs:

            paragraph_length = len(
                paragraph
            )


            # ----------------------------------
            # Oversized paragraph
            # ----------------------------------

            if paragraph_length > self.max_chars:

                # Save accumulated content first.
                flush_chunk()


                temp_chunk = Chunk(
                    id=str(uuid4()),

                    text=paragraph,

                    metadata=ChunkMetadata(
                        chunk_type="fallback",
                    ),
                )


                split_chunks = (
                    self.length_splitter.split(
                        temp_chunk
                    )
                )


                chunks.extend(
                    split_chunks
                )

                continue


            # ----------------------------------
            # Check chunk size
            # ----------------------------------

            separator_length = (
                2
                if current_parts
                else 0
            )


            new_length = (

                current_length

                + separator_length

                + paragraph_length

            )


            if (
                current_parts
                and new_length > self.max_chars
            ):

                flush_chunk()


            # ----------------------------------
            # Add paragraph
            # ----------------------------------

            current_parts.append(
                paragraph
            )

            current_length += (

                paragraph_length

                + (
                    2
                    if len(current_parts) > 1
                    else 0
                )
            )


        # ======================================
        # Flush Remaining Content
        # ======================================

        flush_chunk()


        return chunks