from typing import Any

from pydantic import BaseModel, Field


class ChunkMetadata(BaseModel):
    """
    Metadata describing the structural position of a chunk.
    """

    # ==========================================
    # Contract / Document
    # ==========================================

    contract_id: str | None = None

    document_id: str | None = None

    page: int | None = None

    # ==========================================
    # Legal hierarchy
    # ==========================================

    article: str | None = None

    clause: str | None = None

    point: str | None = None

    section_title: str | None = None

    # ==========================================
    # Chunk information
    # ==========================================

    chunk_type: str = "unknown"

    # ==========================================
    # Parent / hierarchy
    # ==========================================

    parent_chunk_id: str | None = None

    hierarchy_path: str | None = None

    # ==========================================
    # Length split information
    # ==========================================

    chunk_part: int | None = None

    total_parts: int | None = None

    # ==========================================
    # Extra metadata
    # ==========================================

    extra: dict[str, Any] = Field(
        default_factory=dict
    )


class Chunk(BaseModel):
    """
    Represents a single retrieval chunk.
    """

    id: str

    text: str

    metadata: ChunkMetadata

    token_count: int | None = None