
from pathlib import Path
import textract

from parser.base_parser import BaseParser


class DOCParser(BaseParser):
    def parse(self, file_path: Path) -> str:
        if not file_path.exists():
            raise FileNotFoundError(
                f"Không tìm thấy file DOC: {file_path}"
            )

        text = textract.process(str(file_path)).decode(
            "utf-8",
            errors="replace",
        )

        return text.strip()
