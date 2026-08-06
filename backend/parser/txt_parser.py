from pathlib import Path
from parser.base_parser import BaseParser

class TxtParser(BaseParser):
    def parse(self, file_path: Path) -> str:
        with file_path.open(mode='r', encoding="utf-8") as f:
            return f.read().strip()