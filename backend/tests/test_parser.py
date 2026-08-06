from pathlib import Path 
from parser.pdf_parser import PDFParser
from parser.parser_factory import ParserFactory


path_file = Path(r"D:\legal-ai-assistant\backend\data\sample_contracts\docx_test.docx")
parser = ParserFactory.get_parser(path_file)
text = parser.parse(path_file)
print(text)