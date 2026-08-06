from abc import ABC, abstractmethod
from pathlib import Path


class BaseParser(ABC):
    """
    Abstract base class for all document parsers.

    Every parser must implement the parse() method and
    return the extracted text as a string.
    """

    @abstractmethod
    def parse(self, file_path: Path) -> str:
        """
        Parse a document and extract its text.

        Args:
            file_path (Path): Path to the input document.

        Returns:
            str: Extracted document text.
        """
        raise NotImplementedError