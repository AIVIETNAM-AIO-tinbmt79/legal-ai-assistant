from uuid import uuid4

from chunking.base_chunker import BaseChunker
from chunking.chunk_models import Chunk, ChunkMetadata
from chunking.legal_patterns import match_section


class SectionChunker(BaseChunker):
    """
    Chunk documents by top-level sections.

    Strategy:

        - Content before the first Section -> Preamble chunk
        - 1 Section -> 1 Chunk
        - Content inside the section remains together
    """

    def chunk(self, text: str) -> list[Chunk]:

        if not text or not text.strip():
            return []

        lines = text.splitlines()

        chunks: list[Chunk] = []

        current_section: str | None = None
        current_title: str | None = None

        current_lines: list[str] = []

        def flush_chunk():

            nonlocal current_lines

            chunk_text = "\n".join(current_lines).strip()

            if not chunk_text:
                current_lines = []
                return

            # --------------------------------------
            # Determine chunk type
            # --------------------------------------

            if current_section is None:
                chunk_type = "preamble"
            else:
                chunk_type = "section"

            # --------------------------------------
            # Metadata
            # --------------------------------------

            metadata = ChunkMetadata(
                section_title=current_title,
                chunk_type=chunk_type,
                extra={
                    "section": current_section
                },
            )

            # --------------------------------------
            # Create chunk
            # --------------------------------------

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

            section_match = match_section(line)

            # --------------------------------------
            # New Section
            # --------------------------------------

            if section_match:

                # Save previous content.
                #
                # This can be:
                # - preamble
                # - previous section
                flush_chunk()

                current_section = section_match.group(1)

                title = section_match.group(2)

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