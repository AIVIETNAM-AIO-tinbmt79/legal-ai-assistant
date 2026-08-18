from retrieval.hybrid_retriever import HybridRetriever
from rag.context_builder import ContextBuilder
from rag.prompt_builder import PromptBuilder


class RAGPipeline:
    """
    Main RAG pipeline.

    Query
      ↓
    Hybrid Retrieval
      ↓
    Reranking
      ↓
    Context Building
      ↓
    Prompt Building
      ↓
    LLM
      ↓
    Answer + Sources
    """

    def __init__(
        self,
        retriever: HybridRetriever,
        reranker,
        llm,
        context_builder=None,
        prompt_builder=None,
        retrieval_top_k: int = 20,
        reranker_top_k: int = 5,
    ):

        # ==================================================
        # Components
        # ==================================================

        self.retriever = retriever
        self.reranker = reranker
        self.llm = llm

        self.context_builder = (
            context_builder
            or ContextBuilder()
        )

        self.prompt_builder = (
            prompt_builder
            or PromptBuilder()
        )

        # ==================================================
        # Config
        # ==================================================

        self.retrieval_top_k = retrieval_top_k
        self.reranker_top_k = reranker_top_k

    # ==================================================
    # Retrieve
    # ==================================================

    def retrieve(
        self,
        query: str,
    ):
        """
        Run:

            Hybrid Retrieval
                ↓
            Reranking

        Returns final reranked results.
        """

        if not query or not query.strip():
            return []

        # --------------------------------------------------
        # 1. Hybrid Retrieval
        # --------------------------------------------------

        hybrid_results = self.retriever.retrieve(
            query=query,
            top_k=self.retrieval_top_k,
        )

        if not hybrid_results:
            return []

        # --------------------------------------------------
        # 2. Reranking
        # --------------------------------------------------

        reranked_results = self.reranker.rerank(
            query=query,
            results=hybrid_results,
            top_k=self.reranker_top_k,
        )

        return reranked_results

    # ==================================================
    # Build Prompt
    # ==================================================

    def build_prompt(
        self,
        query: str,
    ) -> str:
        """
        Retrieve relevant chunks and build
        the final LLM prompt.
        """

        results = self.retrieve(
            query
        )

        # --------------------------------------------------
        # Build Context
        # --------------------------------------------------

        context = self.context_builder.build(
            results
        )

        # --------------------------------------------------
        # Build Prompt
        # --------------------------------------------------

        return self.prompt_builder.build(
            query=query,
            context=context,
        )

    # ==================================================
    # Run
    # ==================================================

    def run(
        self,
        query: str,
    ) -> dict:
        """
        Run the complete RAG pipeline.

        Returns:

            {
                "query": ...,
                "results": ...,
                "context": ...,
                "prompt": ...,
                "answer": ...,
                "sources": ...
            }
        """

        # ==================================================
        # Empty query
        # ==================================================

        if not query or not query.strip():

            return {
                "query": query,
                "results": [],
                "context": "",
                "prompt": "",
                "answer": "",
                "sources": [],
            }

        # ==================================================
        # 1. Retrieve
        # ==================================================

        results = self.retrieve(
            query
        )

        # ==================================================
        # 2. Build Context
        # ==================================================

        context = self.context_builder.build(
            results
        )

        # ==================================================
        # 3. Get Sources
        # ==================================================

        sources = (
            self.context_builder.get_sources()
        )

        # ==================================================
        # 4. Build Prompt
        # ==================================================

        prompt = self.prompt_builder.build(
            query=query,
            context=context,
        )

        # ==================================================
        # 5. LLM
        # ==================================================

        answer = self.llm.generate(
            prompt
        )

        # ==================================================
        # 6. Return
        # ==================================================

        return {
            "query": query,
            "results": results,
            "context": context,
            "prompt": prompt,
            "answer": answer,
            "sources": sources,
        }