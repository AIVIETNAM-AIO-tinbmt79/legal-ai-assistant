from retrieval.hybrid_retriever import (
    HybridRetriever,
)

from memory.memory_manager import (
    MemoryManager,
)

from .context_builder import (
    ContextBuilder,
)

from .prompts import (
    build_prompt,
)


class QANodes:
    """
    Nodes used by Contract QA workflow.
    """

    def __init__(
        self,
        retriever: HybridRetriever,
        reranker,
        llm,
        memory_manager: MemoryManager | None = None,
        context_builder: ContextBuilder | None = None,
        retrieval_top_k: int = 20,
        reranker_top_k: int = 5,
    ):

        self.retriever = retriever

        self.reranker = reranker

        self.llm = llm

        self.memory_manager = (
            memory_manager
        )

        self.context_builder = (
            context_builder
            or ContextBuilder()
        )

        self.retrieval_top_k = (
            retrieval_top_k
        )

        self.reranker_top_k = (
            reranker_top_k
        )


    # ========================================================
    # Retrieve
    # ========================================================

    def retrieve(
        self,
        state,
    ):

        query = (
            state.get("query", "")
            or ""
        ).strip()

        contract_id = (
            state.get("contract_id")
        )


        if not query:

            return {
                "retrieval_results": []
            }


        results = (
            self.retriever.retrieve(
                query=query,
                top_k=self.retrieval_top_k,
                contract_id=contract_id,
            )
        )


        return {
            "retrieval_results": results
        }


    # ========================================================
    # Rerank
    # ========================================================

    def rerank(
        self,
        state,
    ):

        query = (
            state.get("query", "")
            or ""
        ).strip()

        results = (
            state.get(
                "retrieval_results",
                [],
            )
        )


        if not query or not results:

            return {
                "reranked_results": []
            }


        reranked_results = (
            self.reranker.rerank(
                query=query,
                results=results,
                top_k=self.reranker_top_k,
            )
        )


        return {
            "reranked_results": (
                reranked_results
            )
        }


    # ========================================================
    # Build Context
    # ========================================================

    def build_context(
        self,
        state,
    ):

        results = (
            state.get(
                "reranked_results",
                [],
            )
        )


        context = (
            self.context_builder.build(
                results
            )
        )


        sources = (
            self.context_builder.get_sources()
        )


        return {
            "context": context,
            "sources": sources,
        }


    # ========================================================
    # Load Memory
    # ========================================================

    def load_memory(
        self,
        state,
    ):

        conversation_id = (
            state.get(
                "conversation_id"
            )
        )


        if (
            not conversation_id
            or self.memory_manager is None
        ):

            return {
                "memory": ""
            }


        memory = (
            self.memory_manager
            .get_memory_prompt(
                conversation_id
            )
        )


        return {
            "memory": memory or ""
        }


    # ========================================================
    # Build Prompt
    # ========================================================

    def build_prompt_node(
        self,
        state,
    ):

        query = (
            state.get("query", "")
            or ""
        )

        context = (
            state.get("context", "")
            or ""
        )

        memory = (
            state.get("memory", "")
            or ""
        )


        prompt = build_prompt(
            query=query,
            context=context,
            memory=memory,
        )


        return {
            "prompt": prompt
        }


    # ========================================================
    # Generate Answer
    # ========================================================

    def generate_answer(
        self,
        state,
    ):

        prompt = (
            state.get("prompt", "")
            or ""
        )


        if not prompt:

            return {
                "answer": ""
            }


        answer = (
            self.llm.generate(
                prompt
            )
        )


        if answer is None:
            answer = ""


        answer = str(answer)

        # Remove Markdown bold
        answer = answer.replace(
            "**",
            "",
        )


        return {
            "answer": answer.strip()
        }


    # ========================================================
    # Save Conversation
    # ========================================================

    def save_conversation(
        self,
        state,
    ):

        conversation_id = (
            state.get(
                "conversation_id"
            )
        )

        query = (
            state.get("query", "")
            or ""
        ).strip()

        answer = (
            state.get("answer", "")
            or ""
        ).strip()


        if (
            not conversation_id
            or self.memory_manager is None
        ):

            return {}


        # ----------------------------------------------------
        # Save user message
        #
        # IMPORTANT:
        # We save this AFTER loading memory.
        # Therefore the current query is not duplicated
        # inside the history used for this answer.
        # ----------------------------------------------------

        if query:

            self.memory_manager.add_user_message(
                conversation_id=conversation_id,
                content=query,
            )


        # ----------------------------------------------------
        # Save assistant message
        # ----------------------------------------------------

        if answer:

            self.memory_manager.add_assistant_message(
                conversation_id=conversation_id,
                content=answer,
            )


        return {}