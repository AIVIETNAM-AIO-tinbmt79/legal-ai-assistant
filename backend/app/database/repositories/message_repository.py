
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.message import MessageModel
from app.database.models.conversation import ConversationModel


class MessageRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        conversation_id: str,
        role: str,
        content: str,
        user_id: str,
    ):
        # Chỉ tạo tin nhắn nếu hội thoại thuộc người dùng này.
        conversation_statement = select(
            ConversationModel
        ).where(
            ConversationModel.id == conversation_id,
            ConversationModel.user_id == user_id,
        )

        conversation = self.db.scalar(conversation_statement)

        if conversation is None:
            return None

        now = datetime.now(timezone.utc)

        message = MessageModel(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role=role,
            content=content,
            created_at=now,
        )

        try:
            self.db.add(message)
            conversation.updated_at = now

            self.db.commit()
            self.db.refresh(message)
            return message
        except Exception:
            self.db.rollback()
            raise

    def get_by_id(self, message_id: str, user_id: str):
        statement = (
            select(MessageModel)
            .join(
                ConversationModel,
                MessageModel.conversation_id
                == ConversationModel.id,
            )
            .where(
                MessageModel.id == message_id,
                ConversationModel.user_id == user_id,
            )
        )
        return self.db.scalar(statement)

    def get_by_conversation(
        self,
        conversation_id: str,
        user_id: str,
    ):
        statement = (
            select(MessageModel)
            .join(
                ConversationModel,
                MessageModel.conversation_id
                == ConversationModel.id,
            )
            .where(
                MessageModel.conversation_id == conversation_id,
                ConversationModel.user_id == user_id,
            )
            .order_by(MessageModel.created_at.asc())
        )
        return list(self.db.scalars(statement).all())

    def delete(self, message_id: str, user_id: str):
        message = self.get_by_id(message_id, user_id)

        if message is None:
            return False

        try:
            self.db.delete(message)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise
