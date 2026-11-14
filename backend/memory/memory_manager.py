
from sqlalchemy.orm import Session

from memory.conversation import Conversation
from memory.conversation_memory import ConversationMemory

from app.database.repositories.conversation_repository import (
    ConversationRepository,
)
from app.database.repositories.message_repository import (
    MessageRepository,
)


class MemoryManager:
    def __init__(
        self,
        db: Session,
        max_messages: int = 10,
    ):
        self.db = db
        self.max_messages = max_messages

        self.conversation_repository = ConversationRepository(db)
        self.message_repository = MessageRepository(db)

    def get_conversation(
        self,
        conversation_id: str,
        user_id: str,
    ) -> ConversationMemory | None:
        # 1. Kiểm tra hội thoại có thuộc người dùng không.
        conversation_model = self.conversation_repository.get_by_id(
            conversation_id=conversation_id,
            user_id=user_id,
        )

        if conversation_model is None:
            return None

        # 2. Tạo đối tượng memory cho hội thoại.
        conversation = Conversation(
            conversation_id=conversation_model.id,
            title=conversation_model.title,
        )

        memory = ConversationMemory(
            conversation=conversation,
            max_messages=self.max_messages,
        )

        # 3. Đọc lịch sử từ database.
        messages = self.message_repository.get_by_conversation(
            conversation_id=conversation_id,
            user_id=user_id,
        )

        # Chỉ lấy các tin nhắn gần nhất.
        if self.max_messages > 0:
            messages = messages[-self.max_messages:]
        else:
            messages = []

        # 4. Nạp lịch sử vào memory.
        for message in messages:
            memory.add_message(
                role=message.role,
                content=message.content,
            )

        return memory

    def get_memory_prompt(
        self,
        conversation_id: str,
        user_id: str,
    ) -> str:
        memory = self.get_conversation(
            conversation_id=conversation_id,
            user_id=user_id,
        )

        if memory is None:
            return ""

        return memory.to_prompt()
