from dataclasses import dataclass
from typing import Any

from chunking.chunk_models import Chunk


@dataclass
class RetrievalResult:
    """
    Standard result returned by every retriever.
    """

    chunk: Chunk
    score: float
    source: str
    metadata: dict[str, Any] | None = None