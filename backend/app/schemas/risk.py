
from typing import Any, Literal

from pydantic import BaseModel, Field


class RiskAssessmentRequest(BaseModel):
    contract_id: str = Field(
        min_length=1,
        description="ID của hợp đồng cần đánh giá.",
    )


class RiskAssessmentResponse(BaseModel):
    contract_id: str
    risk_level: Literal["low", "medium", "high"]
    summary: str
    issues: list[dict[str, Any]] = Field(
        default_factory=list
    )
    recommendations: list[str] = Field(
        default_factory=list
    )
