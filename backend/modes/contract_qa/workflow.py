from langgraph.graph import (
    StateGraph,
    START,
    END,
)

from .schemas import (
    QAState,
    QAResult,
)

from .nodes import (
    QANodes,
)


class QAChain:
    """
    Contract QA pipeline.

    Flow:

        START
          ↓
        retrieve
          ↓
        rerank
          ↓
        build_context
          ↓
        load_memory
          ↓
        build_prompt
          ↓
        generate_answer
          ↓
        save_conversation
          ↓
        END
    """

    def __init__(
        self,
        retriever,
        reranker,
        llm,
        memory_manager=None,
        retrieval_top_k: int = 20,
        reranker_top_k: int = 5,
        max_context_chars: int = 20000,
    ):

        from .context_builder import (
            ContextBuilder,
        )


        context_builder = (
            ContextBuilder(
                max_context_chars=(
                    max_context_chars
                )
            )
        )


        self.nodes = QANodes(
            retriever=retriever,
            reranker=reranker,
            llm=llm,
            memory_manager=memory_manager,
            context_builder=context_builder,
            retrieval_top_k=retrieval_top_k,
            reranker_top_k=reranker_top_k,
        )


        self.graph = (
            self._build_graph()
        )


    # ========================================================
    # Build Graph
    # ========================================================

    def _build_graph(self):

        graph = StateGraph(
            QAState
        )


        # ----------------------------------------------------
        # Nodes
        # ----------------------------------------------------

        graph.add_node(
            "retrieve",
            self.nodes.retrieve,
        )

        graph.add_node(
            "rerank",
            self.nodes.rerank,
        )

        graph.add_node(
            "build_context",
            self.nodes.build_context,
        )

        graph.add_node(
            "load_memory",
            self.nodes.load_memory,
        )

        graph.add_node(
            "build_prompt",
            self.nodes.build_prompt_node,
        )

        graph.add_node(
            "generate_answer",
            self.nodes.generate_answer,
        )

        graph.add_node(
            "save_conversation",
            self.nodes.save_conversation,
        )


        # ----------------------------------------------------
        # Edges
        # ----------------------------------------------------

        graph.add_edge(
            START,
            "retrieve",
        )

        graph.add_edge(
            "retrieve",
            "rerank",
        )

        graph.add_edge(
            "rerank",
            "build_context",
        )

        graph.add_edge(
            "build_context",
            "load_memory",
        )

        graph.add_edge(
            "load_memory",
            "build_prompt",
        )

        graph.add_edge(
            "build_prompt",
            "generate_answer",
        )

        graph.add_edge(
            "generate_answer",
            "save_conversation",
        )

        graph.add_edge(
            "save_conversation",
            END,
        )


        return graph.compile()


    # ========================================================
    # Run
    # ========================================================

    def run(
        self,
        query: str,
        contract_id: str | None = None,
        conversation_id: str | None = None,
    ) -> QAResult:

        query = (
            query or ""
        ).strip()


        if not query:

            return QAResult(
                query=query,
                contract_id=contract_id,
                conversation_id=conversation_id,
                answer="",
            )


        initial_state: QAState = {

            "query": query,

            "contract_id": (
                contract_id
            ),

            "conversation_id": (
                conversation_id
            ),

        }


        final_state = (
            self.graph.invoke(
                initial_state
            )
        )


        return QAResult(

            query=query,

            contract_id=contract_id,

            conversation_id=conversation_id,

            answer=(
                final_state.get(
                    "answer",
                    "",
                )
            ),

            retrieval_results=(
                final_state.get(
                    "retrieval_results",
                    [],
                )
            ),

            reranked_results=(
                final_state.get(
                    "reranked_results",
                    [],
                )
            ),

            context=(
                final_state.get(
                    "context",
                    "",
                )
            ),

            memory=(
                final_state.get(
                    "memory",
                    "",
                )
            ),

            prompt=(
                final_state.get(
                    "prompt",
                    "",
                )
            ),

            sources=(
                final_state.get(
                    "sources",
                    [],
                )
            ),
        )


    # ========================================================
    # Conversation
    # ========================================================

    def create_conversation(
        self,
        user_id: str,
        title: str = "New Conversation",
    ):

        if self.nodes.memory_manager is None:

            raise RuntimeError(
                "MemoryManager is not configured."
            )


        return (
            self.nodes.memory_manager
            .create_conversation(
                user_id=user_id,
                title=title,
            )
        )


    def get_conversation(
        self,
        conversation_id: str,
    ):

        if self.nodes.memory_manager is None:

            return None


        return (
            self.nodes.memory_manager
            .get_conversation(
                conversation_id
            )
        )


# ============================================================
# Factory
# ============================================================

def build_qa_chain(
    retriever,
    reranker,
    llm,
    memory_manager=None,
    retrieval_top_k: int = 20,
    reranker_top_k: int = 5,
    max_context_chars: int = 20000,
) -> QAChain:

    return QAChain(

        retriever=retriever,

        reranker=reranker,

        llm=llm,

        memory_manager=memory_manager,

        retrieval_top_k=retrieval_top_k,

        reranker_top_k=reranker_top_k,

        max_context_chars=max_context_chars,

    )