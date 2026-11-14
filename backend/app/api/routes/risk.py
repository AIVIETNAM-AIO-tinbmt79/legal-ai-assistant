
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database.database import get_db
from app.database.repositories.contract_repository import (
    ContractRepository,
)
from app.schemas.risk import (
    RiskAssessmentRequest,
    RiskAssessmentResponse,
)

from modes.risk_assessment.service import RiskService


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/risk",
    tags=["Risk Assessment"],
)
risk_service = RiskService()

@router.post(
    "/assess",
    response_model=RiskAssessmentResponse,
)
def assess_contract_risk(
    request: RiskAssessmentRequest,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    contract_id = request.contract_id.strip()

    if not contract_id:
        raise HTTPException(
            status_code=400,
            detail="contract_id không được để trống.",
        )

    # Bước 1: Kiểm tra hợp đồng có thuộc tài khoản hiện tại.
    repository = ContractRepository(db)

    contract = repository.get_by_id(
        contract_id=contract_id,
        user_id=user_id,
    )

    if contract is None:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy hợp đồng.",
        )

    # Bước 2: Chạy pipeline đánh giá rủi ro.
    try:
        assessment = risk_service.assess(
            contract_id=contract_id
        )

        if hasattr(assessment, "model_dump"):
            result = assessment.model_dump(mode="json")
        else:
            result = assessment.dict()

        return RiskAssessmentResponse(
            contract_id=contract_id,
            **result,
        )

    except ValueError as exc:
        logger.warning(
            "Không thể đánh giá hợp đồng %s: %s",
            contract_id,
            exc,
        )
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.exception(
            "Risk assessment failed for contract %s.",
            contract_id,
        )
        raise HTTPException(
            status_code=500,
            detail="Không thể đánh giá rủi ro hợp đồng.",
        ) from exc
