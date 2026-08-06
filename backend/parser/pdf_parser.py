from pathlib import Path
import fitz
from parser.base_parser import BaseParser

class PDFParser(BaseParser):
    def parse(self, file_path: Path) -> str:
        text = []
        with fitz.open(file_path) as pdf:
            for page in pdf:
                page_text = page.get_text().strip()

                if page_text:
                    text.append(page_text)
        return "\n".join(text)
