import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, DateTime
)

from sqlalchemy.orm import relationship

from app.database.database import Base

class UserModel(Base):
    __tablename__ = "users"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(
            uuid.uuid4()
        ),
    )

    username = Column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )

    email = Column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    password_hash = Column(
        String(255),
        nullable=False,
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

    conversations = relationship(
        "ConversationModel",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    contracts = relationship(
        "ContractModel",
        back_populates="user",
        cascade="all, delete-orphan",
    )