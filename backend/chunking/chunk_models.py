from typing import Any

from pydantic import BaseModel, Field


from pydantic import BaseModel, Field


class ChunkMetadata(BaseModel):
    document_id: str | None = None
    page: int | None = None

    article: str | None = None
    section_title: str | None = None

    chunk_type: str = "unknown"

    chunk_part: int | None = None
    total_parts: int | None = None

    extra: dict = Field(default_factory=dict)


class Chunk(BaseModel):
    """
    Represents a single retrieval chunk.
    """

    id: str

    text: str

    metadata: ChunkMetadata

    token_count: int | None = None