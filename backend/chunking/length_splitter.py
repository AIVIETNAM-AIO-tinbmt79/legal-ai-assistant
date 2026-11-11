from uuid import uuid4

from chunking.chunk_models import Chunk


class LengthSplitter:

    def __init__(
        self,
        max_chars: int = 6000,
        overlap: int = 300,
    ):

        if max_chars <= 0:

            raise ValueError(
                "max_chars must be greater than 0"
            )

        if overlap < 0:

            raise ValueError(
                "overlap cannot be negative"
            )

        if overlap >= max_chars:

            raise ValueError(
                "overlap must be smaller than max_chars"
            )

        self.max_chars = max_chars

        self.overlap = overlap

    def split(
        self,
        chunk: Chunk,
    ) -> list[Chunk]:

        # ==========================================
        # No need to split
        # ==========================================

        if len(chunk.text) <= self.max_chars:

            return [chunk]

        text = chunk.text

        step = (
            self.max_chars
            - self.overlap
        )

        parts = []

        start = 0

        while start < len(text):

            end = (
                start
                + self.max_chars
            )

            part = text[
                start:end
            ].strip()

            if part:

                parts.append(
                    part
                )

            start += step

        total_parts = len(parts)

        result = []

        for index, part in enumerate(
            parts,
            start=1,
        ):

            metadata = (
                chunk.metadata.model_copy(
                    update={
                        "chunk_part": index,

                        "total_parts": total_parts,
                    }
                )
            )

            result.append(
                Chunk(

                    id=str(uuid4()),

                    text=part,

                    metadata=metadata,

                    token_count=None,
                )
            )

        return result