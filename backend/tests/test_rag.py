import os

from dotenv import load_dotenv

from retrieval.retriever_factory import RetrieverFactory
from reranking.reranker_factory import RerankerFactory

from rag.rag_pipeline import RAGPipeline

from llm.llm_factory import LLMFactory


# ==================================================
# Load environment
# ==================================================

load_dotenv()


# ==================================================
# CONFIG
# ==================================================

RETRIEVAL_TOP_K = 20
RERANKER_TOP_K = 5

RERANKER_MAX_LENGTH = 1024
RERANKER_SEGMENT_TOKENS = 450
RERANKER_SEGMENT_OVERLAP = 50


# ==================================================
# Reranker model
# ==================================================

RERANKER_MODEL = os.getenv(
    "RERANKER_MODEL"
)

if not RERANKER_MODEL:
    raise ValueError(
        "RERANKER_MODEL is not configured."
    )


# ==================================================
# 1. Hybrid Retriever
# ==================================================

print()
print("=" * 70)
print("1. INITIALIZING HYBRID RETRIEVER")
print("=" * 70)

retriever = RetrieverFactory.create(
    retriever_type="hybrid",
    top_k=RETRIEVAL_TOP_K,
    retrieval_k=RETRIEVAL_TOP_K,
    semantic_weight=0.7,
    bm25_weight=0.3,
)

print("Semantic weight : 0.7")
print("BM25 weight     : 0.3")
print("Retrieval top_k :", RETRIEVAL_TOP_K)


# ==================================================
# 2. Reranker
# ==================================================

print()
print("=" * 70)
print("2. INITIALIZING RERANKER")
print("=" * 70)

print("Model:", RERANKER_MODEL)

reranker = RerankerFactory.create(
    reranker_type="cross_encoder",
    model_name=RERANKER_MODEL,
    max_length=RERANKER_MAX_LENGTH,
    segment_tokens=RERANKER_SEGMENT_TOKENS,
    segment_overlap=RERANKER_SEGMENT_OVERLAP,
)


# ==================================================
# 3. LLM
# ==================================================

print()
print("=" * 70)
print("3. INITIALIZING LLM")
print("=" * 70)

llm = LLMFactory.create()

print(
    "LLM:",
    type(llm).__name__,
)

print(
    "Model:",
    llm.model,
)


# ==================================================
# 4. RAG Pipeline
# ==================================================

print()
print("=" * 70)
print("4. INITIALIZING RAG PIPELINE")
print("=" * 70)

rag = RAGPipeline(
    retriever=retriever,
    reranker=reranker,
    llm=llm,
    retrieval_top_k=RETRIEVAL_TOP_K,
    reranker_top_k=RERANKER_TOP_K,
)

print("RAG Pipeline ready.")


# ==================================================
# 5. Interactive Q&A
# ==================================================

print()
print("=" * 70)
print("RAG SYSTEM READY")
print("=" * 70)

print()
print("Pipeline:")
print(
    "Query"
    " → Hybrid Top 20"
    " → Reranker Top 5"
    " → Context"
    " → Prompt"
    " → LLM"
)

print()
print("Nhập 'exit' hoặc 'quit' để thoát.")


while True:

    print()
    print("-" * 70)

    query = input(
        "Câu hỏi: "
    ).strip()

    # ==================================================
    # Exit
    # ==================================================

    if query.lower() in {
        "exit",
        "quit",
    }:

        print()
        print("Đã thoát RAG.")
        break

    # ==================================================
    # Empty query
    # ==================================================

    if not query:

        print(
            "Vui lòng nhập câu hỏi."
        )

        continue

    # ==================================================
    # Run RAG
    # ==================================================

    print()
    print("Đang xử lý...")

    try:

        result = rag.run(
            query=query
        )

    except Exception as e:

        print()
        print("=" * 70)
        print("RAG ERROR")
        print("=" * 70)

        print(
            type(e).__name__,
            ":",
            e,
        )

        continue

    # ==================================================
    # Results
    # ==================================================

    results = result.get(
        "results",
        []
    )

    print()
    print("=" * 70)
    print("RETRIEVAL RESULTS")
    print("=" * 70)

    print(
        "Final results:",
        len(results),
    )

    for rank, item in enumerate(
        results,
        start=1,
    ):

        print()
        print(
            f"RANK {rank}"
        )

        print(
            "Chunk ID:",
            item.chunk.id,
        )

        print(
            "Reranker score:",
            item.score,
        )

        print(
            "Source:",
            item.source,
        )

        print(
            "Text preview:"
        )

        print(
            item.chunk.text[:500]
        )

    # ==================================================
    # Context
    # ==================================================

    context = result.get(
        "context",
        ""
    )

    print()
    print("=" * 70)
    print("CONTEXT")
    print("=" * 70)

    print(
        "Context length:",
        len(context),
    )

    print(
        context
    )

    # ==================================================
    # Prompt
    # ==================================================

    prompt = result.get(
        "prompt",
        ""
    )

    print()
    print("=" * 70)
    print("PROMPT")
    print("=" * 70)

    print(
        "Prompt length:",
        len(prompt),
    )

    print(
        prompt
    )

    # ==================================================
    # Answer
    # ==================================================

    answer = result.get(
        "answer",
        ""
    )

    print()
    print("=" * 70)
    print("ANSWER")
    print("=" * 70)

    print(
        answer
    )

    # ==================================================
    # Answer debug
    # ==================================================

    print()
    print(
        "Answer type:",
        type(answer),
    )

    print(
        "Answer repr:",
        repr(answer),
    )