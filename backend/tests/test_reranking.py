from retrieval.retriever_factory import RetrieverFactory
from reranking.reranker_factory import RerankerFactory


# ==================================================
# CONFIG
# ==================================================

QUERY = (
    "Bên A có nghĩa vụ "
    "thanh toán cho Bên B như thế nào?"
)

HYBRID_TOP_K = 20
RERANKER_TOP_K = 5


# ==================================================
# 1. Create Hybrid Retriever
# ==================================================

print()
print("=" * 70)
print("1. HYBRID RETRIEVAL")
print("=" * 70)

retriever = RetrieverFactory.create(
    retriever_type="hybrid",

    top_k=HYBRID_TOP_K,

    retrieval_k=HYBRID_TOP_K,

    semantic_weight=0.7,

    bm25_weight=0.3,
)


# ==================================================
# 2. Hybrid Retrieval
# ==================================================

hybrid_results = retriever.retrieve(
    query=QUERY,
    top_k=HYBRID_TOP_K,
)


print()
print("Query:")
print(QUERY)

print()
print(
    "Hybrid candidates:",
    len(hybrid_results),
)


# ==================================================
# Display Hybrid Results
# ==================================================

for rank, result in enumerate(
    hybrid_results,
    start=1,
):

    print()
    print("-" * 70)

    print("HYBRID RANK:", rank)

    print("Chunk ID:")
    print(result.chunk.id)

    print("Hybrid score:")
    print(result.score)

    print("Source:")
    print(result.source)

    print("Metadata:")
    print(result.chunk.metadata)

    print()
    print("Text:")
    print(result.chunk.text[:1000])


# ==================================================
# 3. Create Reranker
# ==================================================

print()
print("=" * 70)
print("2. RERANKING")
print("=" * 70)

reranker = RerankerFactory.create(
    reranker_type="cross_encoder",

    model_name=(
        "cross-encoder/ms-marco-MiniLM-L-6-v2"
    ),

    max_length=1024,

    segment_tokens=450,

    segment_overlap=50,
)


# ==================================================
# 4. Rerank
# ==================================================

reranked_results = reranker.rerank(
    query=QUERY,

    results=hybrid_results,

    top_k=RERANKER_TOP_K,
)


# ==================================================
# 5. Display Final Results
# ==================================================

print()
print("=" * 70)
print("3. FINAL RERANKED RESULTS")
print("=" * 70)

print()
print("Query:")
print(QUERY)

print()

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

    print()
    print("Chunk ID:")
    print(result.chunk.id)

    print()
    print("Reranker score:")
    print(result.score)

    print()
    print("Source:")
    print(result.source)

    print()
    print("Metadata:")
    print(result.chunk.metadata)

    print()
    print("Text:")
    print("-" * 70)

    print(result.chunk.text)

    print("-" * 70)