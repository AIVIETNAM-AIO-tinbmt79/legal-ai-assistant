
from sqlalchemy.orm import Session
from memory.memory_manager import MemoryManager
from llm.llm_factory import LLMFactory
from retrieval.hybrid_retriever import HybridRetriever
from reranking.reranker_factory import RerankerFactory
from modes.contract_qa.workflow import build_qa_chain

from app.database.repositories.contract_repository import (
    ContractRepository,
)
from app.database.repositories.conversation_repository import (
    ConversationRepository,
)
from app.database.repositories.message_repository import (
    MessageRepository,
)
from app.core.ai_components import AIComponents

class ChatService:
    def __init__(
        self,
        db: Session,
        ai: AIComponents,
    ):
        self.db = db

        # Tái sử dụng model đã được khởi tạo.
        self.retriever = ai.retriever
        self.reranker = ai.reranker
        self.llm = ai.llm

        # Giữ nguyên các repository hiện có.
        self.contract_repository = ContractRepository(db)
        self.conversation_repository = ConversationRepository(db)
        self.message_repository = MessageRepository(db)

        # Giữ nguyên cách xây dựng QA pipeline.
        self.memory_manager = MemoryManager(
            db=db,
            max_messages=10,
        )

        self.qa_chain = build_qa_chain(
            retriever=self.retriever,
            reranker=self.reranker,
            llm=self.llm,
            memory_manager=self.memory_manager,
        )

    def chat(
        self,
        user_id: str,
        query: str,
        conversation_id: str | None = None,
    ) -> dict:
        query = query.strip()

        if not query:
            raise ValueError(
                "Nội dung câu hỏi không được để trống."
            )

        # 1. Tìm hợp đồng đang được kích hoạt.
        contracts = self.contract_repository.get_by_user(user_id)

        active_contract = next(
            (
                contract
                for contract in contracts
                if contract.is_active
            ),
            None,
        )

        if active_contract is None:
            raise ValueError(
                "Bạn cần chọn hợp đồng trước khi đặt câu hỏi."
            )

        if active_contract.status != "indexed":
            raise ValueError(
                "Hợp đồng chưa được lập chỉ mục thành công."
            )

        # 2. Kiểm tra hội thoại hoặc tạo hội thoại mới.
        if conversation_id:
            conversation = self.conversation_repository.get_by_id(
                conversation_id=conversation_id,
                user_id=user_id,
            )

            if conversation is None:
                raise LookupError(
                    "Không tìm thấy hội thoại."
                )
        else:
            title = "[TRA CỨU] " + query[:80]

            conversation = self.conversation_repository.create(
                user_id=user_id,
                title=title,
            )

        # 3. Chạy pipeline QA trước khi lưu tin nhắn.
        # Khi bật memory, lịch sử truy xuất sẽ không chứa
        # câu hỏi hiện tại.
        result = self.qa_chain.run(
            query=query,
            contract_id=active_contract.id,
            conversation_id=conversation.id,
            user_id=user_id,
        )

        answer = (result.answer or "").strip()

        if not answer:
            answer = (
                "Xin lỗi, hệ thống chưa tạo được câu trả lời."
            )

        # 4. Lưu câu hỏi của người dùng.
        user_message = self.message_repository.create(
            conversation_id=conversation.id,
            role="user",
            content=query,
            user_id=user_id,
        )

        if user_message is None:
            raise LookupError(
                "Không thể lưu câu hỏi vào hội thoại."
            )

        # 5. Lưu câu trả lời của AI.
        assistant_message = self.message_repository.create(
            conversation_id=conversation.id,
            role="assistant",
            content=answer,
            user_id=user_id,
        )

        if assistant_message is None:
            raise RuntimeError(
                "Không thể lưu câu trả lời của AI."
            )

        # 6. Trả kết quả cho API.
        return {
            "query": query,
            "contract_id": active_contract.id,
            "conversation_id": conversation.id,
            "answer": answer,
            "sources": result.sources or [],
        }
