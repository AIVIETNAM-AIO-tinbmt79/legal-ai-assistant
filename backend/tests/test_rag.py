from pathlib import Path

from parser.parser_factory import ParserFactory
from parser.cleaner import TextCleaner

from chunking.chunker_factory import ChunkerFactory

from retrieval.hybrid_retriever import HybridRetriever

from reranking.reranker_factory import RerankerFactory

from rag.rag_pipeline import RAGPipeline


# ==================================================
# CONFIG
# ==================================================

PATH_FILE = Path(
    r"D:\legal-ai-assistant\backend\data\sample_contracts\docx_test.docx"
)

QUERY = "Bên A có nghĩa vụ thanh toán cho Bên B như thế nào?"

HYBRID_TOP_K = 20
RERANKER_TOP_K = 5


# ==================================================
# 1. Load document
# ==================================================

print("=" * 70)
print("1. LOAD DOCUMENT")
print("=" * 70)

parser = ParserFactory.get_parser(PATH_FILE)

text = parser.parse(PATH_FILE)

text = TextCleaner.clean(text)

print("Text length:", len(text))


# ==================================================
# 2. Chunk
# ==================================================

print()
print("=" * 70)
print("2. CHUNKING")
print("=" * 70)

chunker = ChunkerFactory.create(text)

chunks = chunker.chunk(text)

print("Chunker:", type(chunker).__name__)
print("Number of chunks:", len(chunks))


# ==================================================
# 3. Hybrid Retriever
# ==================================================

print()
print("=" * 70)
print("3. HYBRID RETRIEVER")
print("=" * 70)

retriever = HybridRetriever(
    chunks=chunks,
    top_k=HYBRID_TOP_K,
    retrieval_k=20,
    semantic_weight=0.7,
    bm25_weight=0.3,
)


# ==================================================
# 4. Reranker
# ==================================================

print()
print("=" * 70)
print("4. RERANKER")
print("=" * 70)

reranker = RerankerFactory.create(
    reranker_type="cross_encoder",
    max_length=1024,
    segment_tokens=450,
    segment_overlap=50,
)


# ==================================================
# 5. Create RAG Pipeline
# ==================================================

print()
print("=" * 70)
print("5. RAG PIPELINE")
print("=" * 70)

rag = RAGPipeline(
    retriever=retriever,
    reranker=reranker,
    retrieval_top_k=HYBRID_TOP_K,
    reranker_top_k=RERANKER_TOP_K,
)


# ==================================================
# 6. Run RAG
# ==================================================

print()
print("=" * 70)
print("6. RUN RAG")
print("=" * 70)

print("Query:")
print(QUERY)

output = rag.run(QUERY)


# ==================================================
# 7. Display Retrieval Results
# ==================================================

results = output["results"]

print()
print("=" * 70)
print("RERANKED RESULTS")
print("=" * 70)

print("Number of final results:", len(results))


for rank, result in enumerate(
    results,
    start=1,
):

    print()
    print("-" * 70)

    print(f"RANK: {rank}")

    print("ID:")
    print(result.chunk.id)

    print("Reranker score:")
    print(result.score)

    print("Metadata:")
    print(result.chunk.metadata)

    print("\nText:")
    print(result.chunk.text)


# ==================================================
# 8. Display Context
# ==================================================

context = output["context"]

print()
print("=" * 70)
print("CONTEXT")
print("=" * 70)

print(context)


# ==================================================
# 9. Display Prompt
# ==================================================

prompt = output["prompt"]

print()
print("=" * 70)
print("PROMPT")
print("=" * 70)

print(prompt)


# ==================================================
# 10. Basic Assertions
# ==================================================

print()
print("=" * 70)
print("TEST")
print("=" * 70)

assert output["query"] == QUERY

assert isinstance(
    output["results"],
    list,
)

assert isinstance(
    output["context"],
    str,
)

assert isinstance(
    output["prompt"],
    str,
)

assert len(results) <= RERANKER_TOP_K

if results:
    assert context.strip() != ""
    assert prompt.strip() != ""

print("RAG PIPELINE TEST PASSED")