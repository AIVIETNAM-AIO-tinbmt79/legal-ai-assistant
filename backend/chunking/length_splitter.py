from uuid import uuid4

from chunking.chunk_models import Chunk


class LengthSplitter:

    def __init__(
        self,
        max_chars: int = 6000,
        overlap: int = 300,
    ):
        if overlap >= max_chars:
            raise ValueError(
                "overlap must be smaller than max_chars"
            )

        self.max_chars = max_chars
        self.overlap = overlap

    def split(self, chunk: Chunk) -> list[Chunk]:

        if len(chunk.text) <= self.max_chars:
            return [chunk]

        text = chunk.text

        step = self.max_chars - self.overlap

        parts = []

        start = 0

        while start < len(text):

            end = start + self.max_chars

            parts.append(
                text[start:end]
            )

            start += step

        total_parts = len(parts)

        result = []

        for index, part in enumerate(
            parts,
            start=1
        ):

            metadata = chunk.metadata.model_copy(
                update={
                    "chunk_part": index,
                    "total_parts": total_parts,
                }
            )

            result.append(
                Chunk(
                    id=str(uuid4()),
                    text=part.strip(),
                    metadata=metadata,
                )
            )

        return result