from retrieval.hybrid_retriever import HybridRetriever
from reranking.reranker_factory import RerankerFactory

from rag.context_builder import ContextBuilder
from rag.prompt_builder import PromptBuilder


class RAGPipeline:
    """
    Main RAG pipeline.

    Flow:

        Query
          ↓
        Hybrid Retrieval
          ↓
        Reranking
          ↓
        Context Builder
          ↓
        Prompt Builder
          ↓
        LLM
    """

    def __init__(
        self,
        retriever: HybridRetriever,
        reranker,
        context_builder: ContextBuilder | None = None,
        prompt_builder: PromptBuilder | None = None,
        retrieval_top_k: int = 20,
        reranker_top_k: int = 5,
    ):

        self.retriever = retriever
        self.reranker = reranker

        self.context_builder = (
            context_builder
            or ContextBuilder()
        )

        self.prompt_builder = (
            prompt_builder
            or PromptBuilder()
        )

        self.retrieval_top_k = retrieval_top_k
        self.reranker_top_k = reranker_top_k

    def retrieve(
        self,
        query: str,
    ):
        """
        Retrieve and rerank relevant chunks.
        """

        # ==========================================
        # 1. Hybrid Retrieval
        # ==========================================

        hybrid_results = self.retriever.retrieve(
            query=query,
            top_k=self.retrieval_top_k,
        )

        if not hybrid_results:
            return []

        # ==========================================
        # 2. Reranking
        # ==========================================

        reranked_results = self.reranker.rerank(
            query=query,
            results=hybrid_results,
            top_k=self.reranker_top_k,
        )

        return reranked_results

    def build_prompt(
        self,
        query: str,
    ) -> str:

        # Retrieve + rerank
        results = self.retrieve(query)

        # Build context
        context = self.context_builder.build(
            results
        )

        # Build prompt
        prompt = self.prompt_builder.build(
            query=query,
            context=context,
        )

        return prompt

    def run(
        self,
        query: str,
    ):
        """
        Run RAG retrieval and build final prompt.

        LLM generation will be connected later.
        """

        results = self.retrieve(query)

        context = self.context_builder.build(
            results
        )

        prompt = self.prompt_builder.build(
            query=query,
            context=context,
        )

        return {
            "query": query,
            "results": results,
            "context": context,
            "prompt": prompt,
        }