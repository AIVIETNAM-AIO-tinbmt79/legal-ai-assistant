from datetime import datetime

from pydantic import BaseModel, Field


class ConversationCreateRequest(BaseModel):
    user_id: str
    title: str = "New Conversation"


class ConversationResponse(BaseModel):
    conversation_id: str
    user_id: str
    title: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ConversationMessage(BaseModel):
    message_id: str
    role: str
    content: str
    created_at: datetime | None = None


class ConversationDetailResponse(BaseModel):
    conversation_id: str
    user_id: str
    title: str

    created_at: datetime | None = None
    updated_at: datetime | None = None

    messages: list[ConversationMessage] = Field(
        default_factory=list
    )