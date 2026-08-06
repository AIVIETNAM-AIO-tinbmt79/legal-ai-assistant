from docx import Document
from pathlib import Path
from parser.base_parser import BaseParser

class DocxParser(BaseParser):
    def parse(self, file_path: Path):
        document = Document(file_path)
        paragraphs = [
            paragraph.text.strip() for paragraph in document.paragraphs
            if paragraph.text.strip()
        ]
        return "\n".join(paragraphs)