from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_current_user
from app.api.schemas.risk import RiskAssessmentResponse
from app.database.repositories.contract import ContractRepository
from modes.risk_assessment.service import RiskService


router = APIRouter(prefix="/risk", tags=["Risk Assessment"])


@router.post("/assess", response_model=RiskAssessmentResponse)
def assess_contract_risk(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    contract_repository = ContractRepository(db)

    contract = contract_repository.get_active_by_user(
        user_id=current_user.id
    )

    if contract is None:
        raise HTTPException(
            status_code=400,
            detail="No active contract selected.",
        )

    if contract.status != "indexed":
        raise HTTPException(
            status_code=400,
            detail=(
                f"Active contract is not ready. "
                f"Current status: {contract.status}"
            ),
        )

    try:
        risk_service = RiskService()
        result = risk_service.assess(contract.id)

        return RiskAssessmentResponse(
            contract_id=contract.id,
            risk_level=result.risk_level,
            summary=result.summary,
            issues=result.issues,
            recommendations=result.recommendations,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Risk assessment failed: {str(exc)}",
        )