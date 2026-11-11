from typing import Literal, TypedDict

from pydantic import BaseModel, Field


class ContractChunk(BaseModel):
    id: str
    text: str
    article: str | None = None
    clause: str | None = None
    point: str | None = None
    hierarchy_path: str | None = None
    chunk_type: str = "unknown"
    parent_chunk_id: str | None = None


class Risk(BaseModel):
    chunk_id: str
    risk_type: str
    description: str
    severity: Literal["low", "medium", "high"]
    reason: str


class BatchRiskResult(BaseModel):
    agent: Literal["agent_1", "agent_2"]
    batch_id: str
    risks: list[Risk] = Field(default_factory=list)


class AgentIssue(BaseModel):
    issue_id: str
    risk_type: str
    description: str
    related_chunk_ids: list[str] = Field(default_factory=list)
    severity: Literal["low", "medium", "high"]
    legal_question: str


class LegalSearchRequest(BaseModel):
    query: str
    search_phrases: list[str] = Field(default_factory=list)
    entity_types: list[str] = Field(default_factory=list)
    relationship_types: list[str] = Field(default_factory=list)
    top_k: int = 5


class LegalReference(BaseModel):
    chunk_id: str
    title: str = ""
    article: str | None = None
    clause: str | None = None
    point: str | None = None
    content: str = ""
    score: float = 0.0


class LegalToolResult(BaseModel):
    query: str
    references: list[LegalReference] = Field(default_factory=list)
    search_count: int = 0


class VerifiedIssue(BaseModel):
    issue_id: str
    risk_type: str
    description: str
    contract_chunk_ids: list[str] = Field(default_factory=list)
    severity: Literal["low", "medium", "high"]

    legal_references: list[LegalReference] = Field(default_factory=list)

    evidence_type: Literal[
        "direct_contradictory",
        "direct_supportive",
        "related_not_applicable",
        "insufficient",
    ]

    legal_confidence: Literal["low", "medium", "high"]

    analysis: str
    conclusion: str


class Agent3Decision(BaseModel):
    action: Literal[
        "search_legal",
        "drop",
        "keep",
        "final",
    ]

    reasoning: str = ""

    search_request: LegalSearchRequest | None = None

    evidence_type: Literal[
        "direct_contradictory",
        "direct_supportive",
        "related_not_applicable",
        "insufficient",
    ] = "insufficient"

    legal_confidence: Literal[
        "low",
        "medium",
        "high",
    ] = "low"

    analysis: str = ""
    conclusion: str = ""


class AgentTrace(BaseModel):
    step: int
    action: str
    reasoning: str = ""
    issue_id: str | None = None
    tool_query: str | None = None
    references_found: int = 0


class FinalRiskAssessment(BaseModel):
    risk_level: Literal["low", "medium", "high"]
    summary: str
    issues: list[VerifiedIssue] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class RiskAssessmentState(TypedDict, total=False):
    chunks: list[ContractChunk]
    contract_summary: str

    batches: list[list[ContractChunk]]

    agent_1_results: list[BatchRiskResult]
    agent_2_results: list[BatchRiskResult]

    candidate_issues: list[AgentIssue]

    verified_issues: list[VerifiedIssue]

    agent_trace: list[AgentTrace]

    agent3_tool_calls: int

    final_assessment: FinalRiskAssessment