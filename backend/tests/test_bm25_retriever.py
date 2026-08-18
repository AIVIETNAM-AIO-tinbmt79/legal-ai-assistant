from retrieval.bm25_retriever import BM25Retriever


# ==================================================
# CONFIG
# ==================================================

QUERY = (
    "Bên A có nghĩa vụ "
    "thanh toán cho Bên B"
)

INDEX_PATH = (
    "storage/bm25/bm25_index.pkl"
)

TOP_K = 5


# ==================================================
# Create Retriever
# ==================================================

retriever = BM25Retriever(
    index_path=INDEX_PATH,
    top_k=TOP_K,
)


# ==================================================
# Retrieve
# ==================================================

results = retriever.retrieve(
    query=QUERY,
    top_k=TOP_K,
)


# ==================================================
# Display
# ==================================================

print()
print("=" * 70)
print("BM25 RETRIEVAL")
print("=" * 70)

print("Query:")
print(QUERY)

print()

print("Results:")
print(len(results))


for rank, result in enumerate(
    results,
    start=1,
):

    print()
    print("-" * 70)

    print("RANK:")
    print(rank)

    print("SCORE:")
    print(result.score)

    print("SOURCE:")
    print(result.source)

    print("CHUNK ID:")
    print(result.chunk.id)

    print("METADATA:")
    print(result.chunk.metadata)

    print()
    print("TEXT:")
    print(result.chunk.text)