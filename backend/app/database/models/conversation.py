import uuid

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    String,
    ForeignKey,
    DateTime,
)

from sqlalchemy.orm import relationship

from app.database.database import Base


class ConversationModel(Base):

    __tablename__ = "conversations"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(
            uuid.uuid4()
        ),
    )

    # ==================================================
    # User
    # ==================================================

    user_id = Column(
        String,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ==================================================
    # Conversation
    # ==================================================

    title = Column(
        String(255),
        nullable=False,
        default="New Conversation",
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(
            timezone.utc
        ),
    )

    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(
            timezone.utc
        ),
        onupdate=lambda: datetime.now(
            timezone.utc
        ),
    )

    # ==================================================
    # Relationships
    # ==================================================

    user = relationship(
        "UserModel",
        back_populates="conversations",
    )

    messages = relationship(
        "MessageModel",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )