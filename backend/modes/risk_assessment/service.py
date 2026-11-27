from __future__ import annotations

import logging
from typing import Iterable

from chunking.chunk_models import Chunk
from .agent import MAX_LLM_CALLS_PER_RUN, RiskAgentClient
from .chunker import convert_chunks, create_batches, extract_global_terms_map
from .schemas import ContractChunk, FinalRiskAssessment, RiskAssessmentState
from .workflow import get_risk_assessment_graph

logger = logging.getLogger(__name__)


def _normalize_input_chunks(
    chunks: Iterable[Chunk | ContractChunk],
) -> list[ContractChunk]:
    normalized: list[ContractChunk] = []
    for item in chunks:
        if isinstance(item, ContractChunk):
            normalized.append(item)
        else:
            normalized.extend(convert_chunks([item]))
    return normalized


def assess_contract_risks(
    chunks: Iterable[Chunk | ContractChunk],
    contract_summary: str = "",
    model_name: str | None = None,
    max_llm_calls: int = MAX_LLM_CALLS_PER_RUN,
) -> FinalRiskAssessment:
    contract_chunks = _normalize_input_chunks(chunks)
    if not contract_chunks:
        return FinalRiskAssessment(
            risk_level="low",
            summary="Không có nội dung hợp đồng để đánh giá rủi ro.",
            issues=[],
            cross_clause_conflicts=[],
            recommendations=[],
        )

    terms_map = extract_global_terms_map(contract_chunks)
    batches = create_batches(contract_chunks)
    graph = get_risk_assessment_graph()

    with RiskAgentClient(
        model_name=model_name,
        max_calls=max_llm_calls,
    ) as client:
        initial_state: dict = {
            "chunks": contract_chunks,
            "global_terms_map": terms_map,
            "contract_summary": contract_summary,
            "batches": batches,
            "agent_1_results": [],
            "agent_2_results": [],
            "candidate_issues": [],
            "verified_issues": [],
            "agent_trace": [],
            "agent3_tool_calls": 0,
            "cross_clause_conflicts": [],
            "_agent_client": client,
        }
        final_state: RiskAssessmentState = graph.invoke(initial_state)

    assessment = final_state.get("final_assessment")
    if isinstance(assessment, FinalRiskAssessment):
        return assessment

    return FinalRiskAssessment(
        risk_level="low",
        summary="Hoàn tất rà soát nhưng chưa ghi nhận rủi ro pháp lý trực tiếp.",
        issues=final_state.get("verified_issues") or [],
        cross_clause_conflicts=final_state.get("cross_clause_conflicts") or [],
        recommendations=[],
    )