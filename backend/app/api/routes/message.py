
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database.database import get_db
from app.database.repositories.message_repository import MessageRepository
from app.schemas.message import MessageCreate, MessageResponse

router = APIRouter(
    prefix="/conversations/{conversation_id}/messages",
    tags=["Messages"],
)


@router.post(
    "",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_message(
    conversation_id: str,
    data: MessageCreate,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    content = data.content.strip()

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nội dung tin nhắn không được để trống.",
        )

    repository = MessageRepository(db)

    message = repository.create(
        conversation_id=conversation_id,
        role="user",
        content=content,
        user_id=user_id,
    )

    if message is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy hội thoại.",
        )

    return message


@router.get(
    "",
    response_model=list[MessageResponse],
)
def get_messages(
    conversation_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repository = MessageRepository(db)

    messages = repository.get_by_conversation(
        conversation_id=conversation_id,
        user_id=user_id,
    )

    # Repository nên trả None nếu hội thoại không tồn tại
    # hoặc không thuộc người dùng hiện tại.
    if messages is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy hội thoại.",
        )

    return messages


@router.get(
    "/{message_id}",
    response_model=MessageResponse,
)
def get_message(
    conversation_id: str,
    message_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repository = MessageRepository(db)

    message = repository.get_by_id(
        message_id=message_id,
        user_id=user_id,
    )

    if message is None or message.conversation_id != conversation_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy tin nhắn.",
        )

    return message
