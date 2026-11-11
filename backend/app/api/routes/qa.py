from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_current_user,
    get_db,
    get_qa_chain,
)

from app.api.schemas.qa import (
    QAChatRequest,
    QAChatResponse,
)

from app.database.models.user import UserModel

from app.database.repositories.contract import (
    ContractRepository,
)


router = APIRouter(
    prefix="/qa",
    tags=["Contract QA"],
)


@router.post(
    "/chat",
    response_model=QAChatResponse,
)
def chat(
    data: QAChatRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(
        get_current_user
    ),
    qa_chain=Depends(get_qa_chain),
):

    # ==================================================
    # Get Active Contract
    # ==================================================

    contract_repository = (
        ContractRepository(db)
    )

    contract = (
        contract_repository
        .get_active_by_user(
            user_id=current_user.id,
        )
    )

    if contract is None:

        raise HTTPException(
            status_code=400,
            detail="No active contract selected.",
        )

    # ==================================================
    # Check contract status
    # ==================================================

    if contract.status != "indexed":

        raise HTTPException(
            status_code=400,
            detail=(
                "Active contract is not ready. "
                f"Current status: {contract.status}"
            ),
        )

    # ==================================================
    # Run QA
    # ==================================================

    result = qa_chain.run(
        query=data.query,
        contract_id=contract.id,
        conversation_id=data.conversation_id,
    )

    # ==================================================
    # Return result
    # ==================================================

    return QAChatResponse(
        query=result.query,
        contract_id=result.contract_id,
        conversation_id=result.conversation_id,
        answer=result.answer,
        sources=result.sources,
    )