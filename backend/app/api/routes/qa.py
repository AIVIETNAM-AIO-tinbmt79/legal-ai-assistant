
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Request
)
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database.database import get_db
from app.services.chat_service import ChatService
from app.schemas.qa import (
    QAChatRequest,
    QAChatResponse,
)


router = APIRouter(
    prefix="/qa",
    tags=["Contract QA"],
)


@router.post("/chat", response_model=QAChatResponse)
def chat(
    data: QAChatRequest,
    request: Request,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    service = ChatService(
        db=db,
        ai=request.app.state.ai_components,
    )

    try:
        result = service.chat(
            user_id=user_id,
            query=data.query,
            conversation_id=data.conversation_id,
        )
        return QAChatResponse(**result)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )