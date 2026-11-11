from pydantic import BaseModel, Field
from modes.risk_assessment.schemas import VerifiedIssue

class RiskAssessmentRequest(BaseModel):
    pass


# class RiskIssueResponse(BaseModel):
#     issue_id: str
#     risk_type: str
#     description: str
#     related_chunk_ids: list[str] = Field(default_factory=list)
#     severity: str
#     legal_question: str


class RiskAssessmentResponse(BaseModel):
    contract_id: str
    risk_level: str
    summary: str
    issues: list[VerifiedIssue] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)