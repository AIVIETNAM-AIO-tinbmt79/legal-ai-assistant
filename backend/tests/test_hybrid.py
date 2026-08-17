from pathlib import Path

from parser.parser_factory import ParserFactory
from parser.cleaner import TextCleaner

from chunking.chunker_factory import ChunkerFactory

from retrieval.hybrid_retriever import HybridRetriever


# ==========================================
# 1. Load document
# ==========================================

path_file = Path(
    r"D:\legal-ai-assistant\backend\data\sample_contracts\docx_test.docx"
)

parser = ParserFactory.get_parser(path_file)

text = parser.parse(path_file)

text = TextCleaner.clean(text)


# ==========================================
# 2. Chunk
# ==========================================

chunker = ChunkerFactory.create(text)

chunks = chunker.chunk(text)

print("Number of chunks:", len(chunks))


# ==========================================
# 3. Hybrid Retriever
# ==========================================

retriever = HybridRetriever(
    chunks=chunks,
    top_k=5,
    retrieval_k=20,
    semantic_weight=0.7,
    bm25_weight=0.3,
)


# ==========================================
# 4. Query
# ==========================================

query = "Bên A có nghĩa vụ thanh toán cho Bên B"


# ==========================================
# 5. Retrieve
# ==========================================

results = retriever.retrieve(
    query=query,
    top_k=20,
)


# ==========================================
# 6. Display
# ==========================================

print()
print("=" * 70)
print("HYBRID RETRIEVAL")
print("=" * 70)

print("Query:", query)

for rank, result in enumerate(
    results,
    start=1,
):

    print()
    print("-" * 70)

    print("RANK:", rank)

    print("ID:", result.chunk.id)

    print("SCORE:", result.score)

    print("SOURCE:", result.source)

    print("METADATA:")
    print(result.chunk.metadata)

    print("\nTEXT:")
    print(result.chunk.text)