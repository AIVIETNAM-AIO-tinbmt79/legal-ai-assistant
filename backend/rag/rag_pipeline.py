from retrieval.hybrid_retriever import HybridRetriever

from rag.context_builder import ContextBuilder
from rag.prompt_builder import PromptBuilder

from memory.memory_manager import MemoryManager


class RAGPipeline:
    """
    Main RAG pipeline.

    Query
      ↓
    Save User Message
      ↓
    Load Conversation Memory
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
    Save Assistant Message
      ↓
    Answer
    """

    def __init__(
        self,
        retriever: HybridRetriever,
        reranker,
        llm,
        memory_manager: MemoryManager,
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

        self.memory_manager = memory_manager

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
    # Create Conversation
    # ==================================================

    def create_conversation(
        self,
        user_id: str,
        title: str = "New Conversation",
    ):

        return self.memory_manager.create_conversation(
            user_id=user_id,
            title=title,
        )

    # ==================================================
    # Get Conversation
    # ==================================================

    def get_conversation(
        self,
        conversation_id: str,
    ):

        return self.memory_manager.get_conversation(
            conversation_id
        )

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
        conversation_id: str | None = None,
    ) -> str:

        # --------------------------------------------------
        # Retrieve
        # --------------------------------------------------

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
        # Load Conversation Memory
        # --------------------------------------------------

        memory = ""

        if conversation_id:

            memory = (
                self.memory_manager
                .get_memory_prompt(
                    conversation_id
                )
            )

        # --------------------------------------------------
        # Build Prompt
        # --------------------------------------------------

        return self.prompt_builder.build(
            query=query,
            context=context,
            memory=memory,
        )

    # ==================================================
    # Run
    # ==================================================

    def run(
        self,
        query: str,
        conversation_id: str | None = None,
    ) -> dict:

        # ==================================================
        # Validate Query
        # ==================================================

        if not query or not query.strip():

            return {
                "query": query,
                "results": [],
                "context": "",
                "memory": "",
                "prompt": "",
                "answer": "",
            }

        query = query.strip()

        # ==================================================
        # 1. Save User Message
        # ==================================================

        if conversation_id:

            self.memory_manager.add_user_message(
                conversation_id=conversation_id,
                content=query,
            )

        # ==================================================
        # 2. Retrieve
        # ==================================================

        results = self.retrieve(
            query
        )

        # ==================================================
        # 3. Build Context
        # ==================================================

        context = self.context_builder.build(
            results
        )

        # ==================================================
        # 4. Load Conversation Memory
        # ==================================================

        memory = ""

        if conversation_id:

            memory = (
                self.memory_manager
                .get_memory_prompt(
                    conversation_id
                )
            )

        # ==================================================
        # 5. Build Prompt
        # ==================================================

        prompt = self.prompt_builder.build(
            query=query,
            context=context,
            memory=memory,
        )

        # ==================================================
        # 6. LLM
        # ==================================================

        answer = self.llm.generate(
            prompt
        )

        # ==================================================
        # 7. Save Assistant Message
        # ==================================================

        if conversation_id and answer:

            self.memory_manager.add_assistant_message(
                conversation_id=conversation_id,
                content=answer,
            )

        # ==================================================
        # 8. Return
        # ==================================================

        return {
            "query": query,
            "results": results,
            "context": context,
            "memory": memory,
            "prompt": prompt,
            "answer": answer,
        }