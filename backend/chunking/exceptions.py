class ChunkingError(Exception):
    """Base exception for chunking errors."""
    pass


class InvalidDocumentStructureError(ChunkingError):
    """Document structure is invalid or cannot be processed."""
    pass


class ChunkTooLargeError(ChunkingError):
    """A chunk exceeds the allowed size."""
    pass