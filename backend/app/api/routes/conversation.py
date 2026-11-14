
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database.database import get_db
from app.database.repositories.conversation_repository import (
    ConversationRepository,
)
from app.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
)

router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"],
)


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation(
    data: ConversationCreate,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repository = ConversationRepository(db)

    conversation = repository.create(
        user_id=user_id,
        title=data.title.strip() or "New Conversation",
    )

    return conversation


@router.get(
    "",
    response_model=list[ConversationResponse],
)
def get_conversations(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repository = ConversationRepository(db)
    return repository.get_by_user(user_id)


@router.get(
    "/{conversation_id}",
    response_model=ConversationResponse,
)
def get_conversation(
    conversation_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repository = ConversationRepository(db)

    conversation = repository.get_by_id(
        conversation_id=conversation_id,
        user_id=user_id,
    )

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy hội thoại.",
        )

    return conversation


@router.patch(
    "/{conversation_id}",
    response_model=ConversationResponse,
)
def update_conversation(
    conversation_id: str,
    data: ConversationUpdate,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    title = data.title.strip()

    if not title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tiêu đề không được để trống.",
        )

    repository = ConversationRepository(db)

    conversation = repository.update_title(
        conversation_id=conversation_id,
        user_id=user_id,
        title=title,
    )

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy hội thoại.",
        )

    return conversation


@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_conversation(
    conversation_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repository = ConversationRepository(db)

    deleted = repository.delete(
        conversation_id=conversation_id,
        user_id=user_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy hội thoại.",
        )

    return None
