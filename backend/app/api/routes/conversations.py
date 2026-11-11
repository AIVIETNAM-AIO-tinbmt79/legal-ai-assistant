from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from sqlalchemy.orm import Session

from app.database.database import (
    SessionLocal,
)

from app.database.repositories.conversation_repository import (
    ConversationRepository,
)

from app.database.repositories.message_repository import (
    MessageRepository,
)

from api.schemas.conversations import (
    ConversationCreateRequest,
    ConversationResponse,
    ConversationDetailResponse,
    ConversationMessage,
)


router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"],
)


# ============================================================
# DATABASE DEPENDENCY
# ============================================================

def get_db():
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


# ============================================================
# CREATE CONVERSATION
# ============================================================

@router.post(
    "",
    response_model=ConversationResponse,
)
def create_conversation(
    request: ConversationCreateRequest,
    db: Session = Depends(get_db),
):
    repository = ConversationRepository(
        session=db
    )

    conversation = repository.create(
        user_id=request.user_id,
        title=request.title,
    )

    return ConversationResponse(
        conversation_id=conversation.id,
        user_id=conversation.user_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


# ============================================================
# GET USER CONVERSATIONS
# ============================================================

@router.get(
    "/user/{user_id}",
    response_model=list[ConversationResponse],
)
def get_user_conversations(
    user_id: str,
    db: Session = Depends(get_db),
):
    repository = ConversationRepository(
        session=db
    )

    conversations = (
        repository.get_by_user_id(
            user_id=user_id
        )
    )

    return [
        ConversationResponse(
            conversation_id=conversation.id,
            user_id=conversation.user_id,
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        )
        for conversation in conversations
    ]


# ============================================================
# GET CONVERSATION DETAIL
# ============================================================

@router.get(
    "/{conversation_id}",
    response_model=ConversationDetailResponse,
)
def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
):
    conversation_repository = (
        ConversationRepository(
            session=db
        )
    )

    message_repository = (
        MessageRepository(
            session=db
        )
    )

    conversation = (
        conversation_repository
        .get_by_id(
            conversation_id
        )
    )

    if conversation is None:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    messages = (
        message_repository
        .get_by_conversation_id(
            conversation_id
        )
    )

    return ConversationDetailResponse(
        conversation_id=conversation.id,
        user_id=conversation.user_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[
            ConversationMessage(
                message_id=message.id,
                role=message.role,
                content=message.content,
                created_at=message.created_at,
            )
            for message in messages
        ],
    )


# ============================================================
# UPDATE CONVERSATION TITLE
# ============================================================

@router.patch(
    "/{conversation_id}",
    response_model=ConversationResponse,
)
def update_conversation_title(
    conversation_id: str,
    title: str,
    db: Session = Depends(get_db),
):
    repository = ConversationRepository(
        session=db
    )

    conversation = (
        repository.get_by_id(
            conversation_id
        )
    )

    if conversation is None:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    conversation = (
        repository.update_title(
            conversation=conversation,
            title=title,
        )
    )

    return ConversationResponse(
        conversation_id=conversation.id,
        user_id=conversation.user_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


# ============================================================
# DELETE CONVERSATION
# ============================================================

@router.delete(
    "/{conversation_id}",
)
def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
):
    repository = ConversationRepository(
        session=db
    )

    conversation = (
        repository.get_by_id(
            conversation_id
        )
    )

    if conversation is None:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    repository.delete(
        conversation
    )

    return {
        "conversation_id": conversation_id,
        "message": "Conversation deleted successfully.",
    }