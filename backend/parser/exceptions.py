class ParserError(Exception):
    """Base exception for parser module."""
    pass


class UnsupportedFileTypeError(ParserError):
    """Raised when the file extension is not supported."""
    pass