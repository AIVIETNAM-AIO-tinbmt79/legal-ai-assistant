
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.conversation import ConversationModel


class ConversationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        user_id: str,
        title: str = "New Conversation",
    ):
        now = datetime.now(timezone.utc)

        conversation = ConversationModel(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=title,
            created_at=now,
            updated_at=now,
        )

        try:
            self.db.add(conversation)
            self.db.commit()
            self.db.refresh(conversation)
            return conversation
        except Exception:
            self.db.rollback()
            raise

    def get_by_id(self, conversation_id: str, user_id: str):
        statement = select(ConversationModel).where(
            ConversationModel.id == conversation_id,
            ConversationModel.user_id == user_id,
        )
        return self.db.scalar(statement)

    def get_by_user(self, user_id: str):
        statement = (
            select(ConversationModel)
            .where(ConversationModel.user_id == user_id)
            .order_by(ConversationModel.updated_at.desc())
        )
        return list(self.db.scalars(statement).all())

    def update_title(
        self,
        conversation_id: str,
        user_id: str,
        title: str,
    ):
        conversation = self.get_by_id(
            conversation_id,
            user_id,
        )

        if conversation is None:
            return None

        try:
            conversation.title = title
            conversation.updated_at = datetime.now(timezone.utc)

            self.db.commit()
            self.db.refresh(conversation)
            return conversation
        except Exception:
            self.db.rollback()
            raise

    def delete(self, conversation_id: str, user_id: str):
        conversation = self.get_by_id(
            conversation_id,
            user_id,
        )

        if conversation is None:
            return False

        try:
            self.db.delete(conversation)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise
