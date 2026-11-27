from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field, model_validator


RiskLevel = Literal["low", "medium", "high"]
AgentName = Literal["agent_1", "agent_2"]
EvidenceType = Literal[
    "direct_contradictory",
    "direct_supportive",
    "related_not_applicable",
    "insufficient",
]
RedlineAction = Literal["MODIFY", "ADD", "REMOVE", "REVIEW"]


def _coerce_confidence(value: object) -> RiskLevel:
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"low", "medium", "high"}:
            return v  # type: ignore[return-value]
        if v in {"thấp", "min"}:
            return "low"
        if v in {"trung bình", "med", "moderate"}:
            return "medium"
        if v in {"cao", "max", "critical", "nghiêm trọng"}:
            return "high"
    if isinstance(value, (int, float)):
        if value >= 0.7 or value >= 4:
            return "high"
        if value >= 0.35 or value >= 2:
            return "medium"
        return "low"
    return "low"


def _coerce_evidence_type(value: object) -> EvidenceType:
    allowed: set[str] = {
        "direct_contradictory",
        "direct_supportive",
        "related_not_applicable",
        "insufficient",
    }
    if isinstance(value, str):
        v = value.strip().lower()
        if v in allowed:
            return v  # type: ignore[return-value]
        if v in {"contradictory", "conflict", "violation", "mâu thuẫn"}:
            return "direct_contradictory"
        if v in {"supportive", "compliant", "phù hợp"}:
            return "direct_supportive"
        if v in {"not_applicable", "unrelated", "không liên quan"}:
            return "related_not_applicable"
    return "insufficient"


class SchemaModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ContractChunk(SchemaModel):
    id: str
    text: str
    article: str | None = None
    clause: str | None = None
    point: str | None = None
    hierarchy_path: str | None = None
    chunk_type: str = "unknown"
    parent_chunk_id: str | None = None


class RiskSubIssue(SchemaModel):
    risk_type: str
    description: str
    legal_question: str
    needs_web_search: bool = True
    search_queries: list[str] = Field(default_factory=list)


class RiskCandidate(SchemaModel):
    chunk_id: str
    risk_type: str
    description: str
    severity: RiskLevel
    reason: str
    subissues: list[RiskSubIssue] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _normalize_risk_candidate(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        cleaned = dict(data)
        sev = cleaned.get("severity")
        if isinstance(sev, str):
            s = sev.strip().lower()
            if s in {"critical", "severe", "cao", "nghiêm trọng", "rất cao"}:
                cleaned["severity"] = "high"
            elif s in {"medium", "med", "moderate", "trung bình"}:
                cleaned["severity"] = "medium"
            elif s in {"low", "minor", "thấp"}:
                cleaned["severity"] = "low"
        elif isinstance(sev, (int, float)):
            cleaned["severity"] = "high" if sev >= 0.7 or sev >= 4 else ("medium" if sev >= 0.35 or sev >= 2 else "low")
        return cleaned


class AgentAnalysisResult(SchemaModel):
    agent: AgentName
    batch_id: str
    risks: list[RiskCandidate] = Field(default_factory=list)


class MergedRiskCandidate(SchemaModel):
    candidate_id: str
    risk_type: str
    description: str
    related_chunk_ids: list[str] = Field(min_length=1)
    severity: RiskLevel
    reasons: list[str] = Field(default_factory=list)
    detected_by: list[AgentName] = Field(min_length=1)
    legal_question: str
    needs_web_search: bool = True
    search_queries: list[str] = Field(default_factory=list)


class LegalSearchRequest(SchemaModel):
    query: str = Field(min_length=1)
    allowed_domains: list[str] = Field(
        default_factory=lambda: ["chinhphu.vn", "thuvienphapluat.vn"]
    )
    max_results: int = Field(default=5, ge=1, le=10)


class LegalReference(SchemaModel):
    title: str
    url: str
    snippet: str = ""
    content: str = ""
    domain: str = ""
    published_date: str | None = None
    effective_date: str | None = None
    is_official_source: bool = False


class LegalSearchResult(SchemaModel):
    query: str
    references: list[LegalReference] = Field(default_factory=list)
    search_count: int = 0
    errors: list[str] = Field(default_factory=list)


class Agent3Decision(SchemaModel):
    action: Literal["search_legal", "keep", "drop", "final"]
    reasoning: str
    search_request: LegalSearchRequest | None = None
    evidence_type: EvidenceType = "insufficient"
    confidence: RiskLevel = "low"
    analysis: str = ""
    conclusion: str = ""

    @model_validator(mode="before")
    @classmethod
    def _normalize_raw_input(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data

        cleaned = dict(data)

        search_req = cleaned.get("search_request")
        if isinstance(search_req, str):
            q = search_req.strip()
            cleaned["search_request"] = {"query": q} if q else None
        elif isinstance(search_req, dict) and not str(search_req.get("query") or "").strip():
            cleaned["search_request"] = None

        cleaned["evidence_type"] = _coerce_evidence_type(cleaned.get("evidence_type"))
        cleaned["confidence"] = _coerce_confidence(cleaned.get("confidence"))

        if cleaned.get("action") not in {"search_legal", "keep", "drop", "final"}:
            cleaned["action"] = "final"

        for field_name in ("reasoning", "analysis", "conclusion"):
            if cleaned.get(field_name) is None:
                cleaned[field_name] = ""

        return cleaned


class RedlineSuggestion(SchemaModel):
    action: RedlineAction = "MODIFY"
    proposed_text: str = ""
    reason: str = ""


class VerifiedRisk(SchemaModel):
    candidate_id: str
    risk_type: str
    description: str
    contract_chunk_ids: list[str] = Field(min_length=1)
    severity: RiskLevel
    legal_references: list[LegalReference] = Field(default_factory=list)
    evidence_type: Literal["direct_contradictory", "commercial_review"] = (
        "direct_contradictory"
    )
    confidence: RiskLevel
    analysis: str
    conclusion: str
    redline: RedlineSuggestion | None = None


class CrossClauseConflict(SchemaModel):
    conflict_id: str
    involved_clauses: list[str] = Field(min_length=2)
    description: str
    recommendation: str


class FinalRiskAssessment(SchemaModel):
    risk_level: RiskLevel
    summary: str
    issues: list[VerifiedRisk] = Field(default_factory=list)
    cross_clause_conflicts: list[CrossClauseConflict] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class AgentTrace(SchemaModel):
    step: int
    action: str
    reasoning: str = ""
    candidate_id: str | None = None
    tool_query: str | None = None
    references_found: int = 0


class RiskAssessmentState(TypedDict, total=False):
    chunks: list[ContractChunk]
    global_terms_map: dict[str, str]
    contract_summary: str
    batches: list[list[ContractChunk]]
    agent_1_results: Annotated[list[AgentAnalysisResult], operator.add]
    agent_2_results: Annotated[list[AgentAnalysisResult], operator.add]
    candidate_issues: list[MergedRiskCandidate]
    verified_issues: Annotated[list[VerifiedRisk], operator.add]
    agent_trace: Annotated[list[AgentTrace], operator.add]
    agent3_tool_calls: Annotated[int, operator.add]
    cross_clause_conflicts: list[CrossClauseConflict]
    final_assessment: FinalRiskAssessment