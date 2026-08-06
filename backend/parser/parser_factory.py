from pathlib import Path
from parser.base_parser import BaseParser
from parser.pdf_parser import PDFParser
from parser.docx_parser import DocxParser
from parser.txt_parser import TxtParser
from parser.exceptions import UnsupportedFileTypeError

class ParserFactory:
    _PARSERS = {
        ".pdf": PDFParser,
        ".docx": DocxParser,
        ".txt": TxtParser,
    }

    @classmethod
    def get_parser(cls, file_path: Path) -> BaseParser:
        extension = file_path.suffix.lower()

        parser_class = cls._PARSERS.get(extension)

        if parser_class is None:
            raise UnsupportedFileTypeError(
                f"Unsupported file type: {extension}"
            )

        return parser_class()
