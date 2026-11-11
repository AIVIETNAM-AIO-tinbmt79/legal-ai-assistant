import uuid

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Text,
    String,
    ForeignKey,
    DateTime,
)

from sqlalchemy.orm import relationship

from app.database.database import Base


class MessageModel(Base):

    __tablename__ = "messages"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(
            uuid.uuid4()
        ),
    )

    conversation_id = Column(
        String,
        ForeignKey(
            "conversations.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    role = Column(
        String(50),
        nullable=False,
    )

    content = Column(
        Text,
        nullable=False,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(
            timezone.utc
        ),
    )

    conversation = relationship(
        "ConversationModel",
        back_populates="messages",
    )