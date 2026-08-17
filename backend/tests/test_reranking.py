from pathlib import Path

from parser.parser_factory import ParserFactory
from parser.cleaner import TextCleaner

from chunking.chunker_factory import ChunkerFactory

from retrieval.hybrid_retriever import HybridRetriever

from reranking.reranker_factory import RerankerFactory


# ==========================================
# CONFIG
# ==========================================

PATH_FILE = Path(
    r"D:\legal-ai-assistant\backend\data\sample_contracts\docx_test.docx"
)

QUERY = "Bên A có nghĩa vụ thanh toán cho Bên B"

HYBRID_TOP_K = 20
RETRIEVAL_K = 20
RERANKER_TOP_K = 5


# ==========================================
# 1. Load document
# ==========================================

path_file = PATH_FILE

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
    top_k=HYBRID_TOP_K,
    retrieval_k=RETRIEVAL_K,
    semantic_weight=0.7,
    bm25_weight=0.3,
)


# ==========================================
# 4. Hybrid Retrieval
# ==========================================

hybrid_results = retriever.retrieve(
    query=QUERY,
    top_k=HYBRID_TOP_K,
)


# ==========================================
# 5. Display Hybrid Results
# ==========================================

print()
print("=" * 70)
print("HYBRID RETRIEVAL")
print("=" * 70)

print("Query:", QUERY)

print(
    "Hybrid candidates:",
    len(hybrid_results),
)


for rank, result in enumerate(
    hybrid_results,
    start=1,
):

    print()
    print("-" * 70)

    print("HYBRID RANK:", rank)

    print("ID:", result.chunk.id)

    print("SCORE:", result.score)

    print("SOURCE:", result.source)

    print("METADATA:")
    print(result.chunk.metadata)

    print("\nTEXT:")
    print(result.chunk.text[:1000])


# ==========================================
# 6. Reranker
# ==========================================

print()
print("=" * 70)
print("RERANKING")
print("=" * 70)


reranker = RerankerFactory.create(
    reranker_type="cross_encoder",
    max_length=1024,
    segment_tokens=450,
    segment_overlap=50,
)


# ==========================================
# 7. Rerank
# ==========================================

reranked_results = reranker.rerank(
    query=QUERY,
    results=hybrid_results,
    top_k=RERANKER_TOP_K,
)


# ==========================================
# 8. Display Final Results
# ==========================================

print()
print("=" * 70)
print("FINAL RERANKED RESULTS")
print("=" * 70)

print("Query:", QUERY)

print(
    "Hybrid candidates:",
    len(hybrid_results),
)

print(
    "Final results:",
    len(reranked_results),
)


for rank, result in enumerate(
    reranked_results,
    start=1,
):

    print()
    print("=" * 70)

    print("FINAL RANK:", rank)

    print("=" * 70)

    print("ID:", result.chunk.id)

    print("RERANKER SCORE:", result.score)

    print(
        "HYBRID SCORE:",
        result.metadata.get(
            "previous_score"
        ),
    )

    print(
        "PREVIOUS SOURCE:",
        result.metadata.get(
            "previous_source"
        ),
    )

    print("\nMETADATA:")
    print(result.chunk.metadata)

    print("\nTEXT:")
    print("-" * 70)

    print(result.chunk.text)

    print("-" * 70)