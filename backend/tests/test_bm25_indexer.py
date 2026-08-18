from pathlib import Path

from parser.parser_factory import ParserFactory
from parser.cleaner import TextCleaner

from chunking.chunker_factory import ChunkerFactory

from indexing.bm25_indexer import BM25Indexer


# ==================================================
# CONFIG
# ==================================================

PATH_FILE = Path(
    r"D:\legal-ai-assistant\backend\data\sample_contracts\docx_test.docx"
)

INDEX_PATH = Path(
    "storage/bm25/bm25_index.pkl"
)


# ==================================================
# Parse
# ==================================================

parser = ParserFactory.get_parser(
    PATH_FILE
)

text = parser.parse(
    PATH_FILE
)

text = TextCleaner.clean(
    text
)


# ==================================================
# Chunk
# ==================================================

chunker = ChunkerFactory.create(
    text
)

chunks = chunker.chunk(
    text
)

print(
    "Number of chunks:",
    len(chunks),
)


# ==================================================
# Build
# ==================================================

indexer = BM25Indexer(
    index_path=INDEX_PATH
)

indexer.build(
    chunks
)


# ==================================================
# Test
# ==================================================

print()
print("=" * 70)
print("BM25 INDEX")
print("=" * 70)

print(
    "Index path:",
    INDEX_PATH,
)

print(
    "Number of chunks:",
    indexer.size,
)

print(
    "Index ready:",
    indexer.is_ready,
)

print()
print("BM25 INDEX CREATED SUCCESSFULLY")