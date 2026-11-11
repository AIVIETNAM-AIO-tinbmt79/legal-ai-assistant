import os

from dotenv import load_dotenv


from backend.app.database.database import (
    SessionLocal,
    init_db,
)


from backend.app.database.repositories.user_repository import (
    UserRepository,
)


from backend.app.database.repositories.conversation_repository import (
    ConversationRepository,
)


from memory.memory_manager import (
    MemoryManager,
)


from retrieval.retriever_factory import (
    RetrieverFactory,
)


from reranking.reranker_factory import (
    RerankerFactory,
)


from rag.rag_pipeline import (
    RAGPipeline,
)


from llm.llm_factory import (
    LLMFactory,
)


# ==================================================
# Load Environment
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
# Initialize Database
# ==================================================

print()
print("=" * 70)
print("INITIALIZING DATABASE")
print("=" * 70)

init_db()


# ==================================================
# Database Session
# ==================================================

session = SessionLocal()


try:

    # ==================================================
    # 1. User
    # ==================================================

    print()
    print("=" * 70)
    print("1. INITIALIZING USER")
    print("=" * 70)

    user_repository = UserRepository(
        session=session
    )

    TEST_EMAIL = "test_rag@example.com"

    user = user_repository.get_by_email(
        TEST_EMAIL
    )

    if not user:

        user = user_repository.create(
            username="test_rag_user",
            email=TEST_EMAIL,
            password_hash="test_password_hash",
        )

        print(
            "Created test user."
        )

    else:

        print(
            "Using existing test user."
        )

    print(
        "User ID:",
        user.id,
    )


    # ==================================================
    # 2. Memory Manager
    # ==================================================

    print()
    print("=" * 70)
    print("2. INITIALIZING MEMORY MANAGER")
    print("=" * 70)

    memory_manager = MemoryManager(
        session=session,
        max_messages= 10
    )

    print(
        "Memory Manager ready."
    )


    # ==================================================
    # 3. Hybrid Retriever
    # ==================================================

    print()
    print("=" * 70)
    print("3. INITIALIZING HYBRID RETRIEVER")
    print("=" * 70)

    retriever = RetrieverFactory.create(
        retriever_type="hybrid",
        top_k=RETRIEVAL_TOP_K,
        retrieval_k=RETRIEVAL_TOP_K,
        semantic_weight=0.7,
        bm25_weight=0.3,
    )

    print(
        "Hybrid Retriever ready."
    )


    # ==================================================
    # 4. Reranker
    # ==================================================

    print()
    print("=" * 70)
    print("4. INITIALIZING RERANKER")
    print("=" * 70)

    RERANKER_MODEL = os.getenv(
        "RERANKER_MODEL"
    )

    if not RERANKER_MODEL:

        raise ValueError(
            "RERANKER_MODEL is not configured."
        )

    print(
        "Model:",
        RERANKER_MODEL,
    )

    reranker = RerankerFactory.create(
        reranker_type="cross_encoder",
        model_name=RERANKER_MODEL,
        max_length=RERANKER_MAX_LENGTH,
        segment_tokens=RERANKER_SEGMENT_TOKENS,
        segment_overlap=RERANKER_SEGMENT_OVERLAP,
    )

    print(
        "Reranker ready."
    )


    # ==================================================
    # 5. LLM
    # ==================================================

    print()
    print("=" * 70)
    print("5. INITIALIZING LLM")
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
    # 6. RAG Pipeline
    # ==================================================

    print()
    print("=" * 70)
    print("6. INITIALIZING RAG PIPELINE")
    print("=" * 70)

    rag = RAGPipeline(
        retriever=retriever,
        reranker=reranker,
        llm=llm,
        memory_manager=memory_manager,
        retrieval_top_k=RETRIEVAL_TOP_K,
        reranker_top_k=RERANKER_TOP_K,
    )

    print(
        "RAG Pipeline ready."
    )


    # ==================================================
    # 7. Conversation Repository
    # ==================================================

    conversation_repository = (
        ConversationRepository(
            session=session
        )
    )


    # ==================================================
    # 8. Conversation Mode
    # ==================================================

    print()
    print("=" * 70)
    print("CONVERSATION MODE")
    print("=" * 70)

    print()
    print("1. Tạo hội thoại mới")
    print("2. Tiếp tục hội thoại cũ")

    mode = input(
        "\nChọn chế độ (1/2): "
    ).strip()


    # ==================================================
    # MODE 1: New Conversation
    # ==================================================

    if mode == "1":

        print()

        title = input(
            "Tên hội thoại: "
        ).strip()

        if not title:

            title = "New Conversation"

        conversation = rag.create_conversation(
            user_id=user.id,
            title=title,
        )

        conversation_id = (
            conversation
            .conversation
            .conversation_id
        )

        print()
        print(
            "Đã tạo hội thoại mới."
        )

        print(
            "Tên:",
            title,
        )


    # ==================================================
    # MODE 2: Continue Old Conversation
    # ==================================================

    elif mode == "2":

        print()

        conversations = (
            conversation_repository
            .get_by_user_id(
                user_id=user.id
            )
        )

        # ----------------------------------------------
        # No conversations
        # ----------------------------------------------

        if not conversations:

            print()

            print(
                "Bạn chưa có hội thoại nào."
            )

            print(
                "Vui lòng tạo hội thoại mới."
            )

            raise SystemExit


        # ----------------------------------------------
        # Display conversations
        # ----------------------------------------------

        print("=" * 70)
        print("DANH SÁCH HỘI THOẠI")
        print("=" * 70)

        print()

        for index, conversation_model in enumerate(
            conversations,
            start=1,
        ):

            print(
                f"{index}. {conversation_model.title}"
            )

            print(
                f"   Created: "
                f"{conversation_model.created_at}"
            )

            print()


        # ----------------------------------------------
        # Select conversation
        # ----------------------------------------------

        while True:

            choice = input(
                "Chọn hội thoại (nhập số): "
            ).strip()

            try:

                choice = int(choice)

                if (
                    1
                    <= choice
                    <= len(conversations)
                ):

                    break

                print(
                    "Số không hợp lệ."
                )

            except ValueError:

                print(
                    "Vui lòng nhập số."
                )


        selected_conversation = (
            conversations[
                choice - 1
            ]
        )

        conversation_id = (
            selected_conversation.id
        )


        # ----------------------------------------------
        # Load Persistent Memory
        # ----------------------------------------------

        conversation_memory = (
            rag.get_conversation(
                conversation_id
            )
        )

        print()

        print("=" * 70)
        print("ĐÃ LOAD HỘI THOẠI")
        print("=" * 70)

        print()

        print(
            "Tên:",
            selected_conversation.title,
        )

        print(
            "Conversation ID:",
            conversation_id,
        )

        print()

        print("=" * 70)
        print("PREVIOUS CONVERSATION MEMORY")
        print("=" * 70)

        print()

        previous_memory = (
            conversation_memory.to_prompt()
        )

        if previous_memory:

            print(
                previous_memory
            )

        else:

            print(
                "Hội thoại chưa có tin nhắn."
            )


    # ==================================================
    # Invalid Mode
    # ==================================================

    else:

        raise ValueError(
            "Chế độ không hợp lệ."
        )


    # ==================================================
    # 9. RAG Chat Ready
    # ==================================================

    print()

    print("=" * 70)
    print("RAG SYSTEM READY")
    print("=" * 70)

    print()

    print(
        "Nhập 'exit' hoặc 'quit' để thoát."
    )


    # ==================================================
    # Chat Loop
    # ==================================================

    while True:

        print()
        print("-" * 70)

        query = input(
            "Câu hỏi: "
        ).strip()


        # --------------------------------------------------
        # Exit
        # --------------------------------------------------

        if query.lower() in {
            "exit",
            "quit",
        }:

            print()

            print(
                "Đã thoát RAG."
            )

            break


        # --------------------------------------------------
        # Empty Query
        # --------------------------------------------------

        if not query:

            print(
                "Vui lòng nhập câu hỏi."
            )

            continue


        # ==================================================
        # Run RAG
        # ==================================================

        print()
        print(
            "Đang xử lý..."
        )

        try:

            result = rag.run(
                query=query,
                conversation_id=conversation_id,
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
        # Retrieval Results
        # ==================================================

        results = result.get(
            "results",
            [],
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
        # Memory
        # ==================================================

        memory = result.get(
            "memory",
            "",
        )

        print()

        print("=" * 70)
        print("MEMORY USED FOR CURRENT PROMPT")
        print("=" * 70)

        print()

        if memory:

            print(
                memory
            )

        else:

            print(
                "No conversation memory."
            )


        # ==================================================
        # Context
        # ==================================================

        context = result.get(
            "context",
            "",
        )

        print()

        print("=" * 70)
        print("CONTEXT")
        print("=" * 70)

        print(
            context
        )


        # ==================================================
        # Answer
        # ==================================================

        answer = result.get(
            "answer",
            "",
        )

        print()

        print("=" * 70)
        print("ANSWER")
        print("=" * 70)

        print()

        print(
            answer
        )


        # ==================================================
        # Updated Memory
        # ==================================================

        updated_memory = (
            memory_manager.get_memory_prompt(
                conversation_id
            )
        )

        print()

        print("=" * 70)
        print("UPDATED CONVERSATION MEMORY")
        print("=" * 70)

        print()

        print(
            updated_memory
        )


finally:

    session.close()

    print()

    print(
        "Database session closed."
    )