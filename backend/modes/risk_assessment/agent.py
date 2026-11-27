from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, TypeVar

import httpx
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from config.settings import settings
from .prompts import (
    AGENT_1_SYSTEM_PROMPT,
    AGENT_2_SYSTEM_PROMPT,
    AGENT_3_SPLIT_SYSTEM_PROMPT,
    AGENT_3_SYSTEM_PROMPT,
    CROSS_CLAUSE_AUDITOR_SYSTEM_PROMPT,
    REDLINE_GENERATOR_SYSTEM_PROMPT,
    build_agent3_prompt,
    build_batch_prompt,
)
from .schemas import (
    Agent3Decision,
    AgentAnalysisResult,
    ContractChunk,
    CrossClauseConflict,
    LegalReference,
    MergedRiskCandidate,
    RedlineSuggestion,
    RiskCandidate,
    RiskSubIssue,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

MAX_LLM_CALLS_PER_RUN = 120
MAX_AGENT3_SEARCH_CALLS = 2
MAX_AGENT3_STEPS = 4


class RiskAgentLimitExceeded(RuntimeError):
    """Vượt quá giới hạn số lần gọi LLM cho phép trong một lượt đánh giá."""


def _build_chat_completions_url(base_url: str) -> str:
    cleaned = base_url.strip().rstrip("/")
    if cleaned.endswith("/chat/completions"):
        return cleaned
    if cleaned.endswith("/v1"):
        return f"{cleaned}/chat/completions"
    return f"{cleaned}/v1/chat/completions"


class RiskAgentClient:
    def __init__(
        self,
        model_name: str | None = None,
        temperature: float = 0.05,
        max_calls: int = MAX_LLM_CALLS_PER_RUN,
        timeout: float = 60.0,
    ) -> None:
        api_key = getattr(settings, "API_LLM", None) or os.getenv("LLM_API_KEY")
        if not api_key or not str(api_key).strip():
            raise RuntimeError("Thiếu LLM_API_KEY trong cấu hình.")

        base_url = getattr(settings, "LLM_BASE_URL", None) or os.getenv("LLM_BASE_URL")
        if not base_url or not str(base_url).strip():
            raise RuntimeError("Thiếu LLM_BASE_URL trong cấu hình.")

        resolved_model = (
            model_name
            or getattr(settings, "LLM_MODEL", None)
            or os.getenv("LLM_MODEL")
        )
        if not resolved_model or not str(resolved_model).strip():
            raise RuntimeError("Thiếu LLM_MODEL trong cấu hình.")

        self.api_key = str(api_key).strip()
        self.endpoint_url = _build_chat_completions_url(str(base_url))
        self.model_name = str(resolved_model).strip()
        self.temperature = temperature
        self.max_calls = max(1, max_calls)
        self.call_count = 0

        self._http = httpx.Client(
            timeout=httpx.Timeout(timeout, connect=15.0),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> RiskAgentClient:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def remaining_calls(self) -> int:
        return max(0, self.max_calls - self.call_count)

    def _check_budget(self) -> None:
        if self.call_count >= self.max_calls:
            raise RiskAgentLimitExceeded(
                f"Đã chạm giới hạn {self.max_calls} lần gọi LLM trong lượt này."
            )

    @staticmethod
    def _extract_json_payload(raw_text: str) -> Any:
        cleaned = (raw_text or "").strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            obj_match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
            if obj_match:
                return json.loads(obj_match.group(0))
            raise

    @staticmethod
    def _extract_message_content(data: dict[str, Any]) -> str:
        choices = data.get("choices") or []
        if not choices:
            raise ValueError("Phản hồi API không có choices.")
        message = choices[0].get("message") or {}
        content = message.get("content", "")
        if isinstance(content, list):
            parts = [
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and item.get("type") == "text"
            ]
            return "\n".join(parts).strip()
        return str(content or "").strip()

    def _chat(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self.model_name,
            "temperature": self.temperature,
            "messages": [
                {"role": "system", "content": SystemMessage(content=system_prompt).content},
                {"role": "user", "content": HumanMessage(content=user_prompt).content},
            ],
        }
        response = self._http.post(self.endpoint_url, json=payload)
        response.raise_for_status()
        return self._extract_message_content(response.json())

    def invoke_json(
        self,
        system_prompt: str,
        user_prompt: str,
        schema_cls: type[T],
        fallback: T,
    ) -> T:
        self._check_budget()
        self.call_count += 1

        try:
            content = self._chat(system_prompt=system_prompt, user_prompt=user_prompt)
            payload = self._extract_json_payload(content)
            return schema_cls.model_validate(payload)
        except RiskAgentLimitExceeded:
            raise
        except Exception as exc:
            logger.warning(
                "[RiskAgentClient] Parse/invoke fallback for %s: %s",
                schema_cls.__name__,
                exc,
            )
            return fallback


class _BatchRisksPayload(BaseModel):
    risks: list[RiskCandidate] = []


class _SplitSubissuesPayload(BaseModel):
    subissues: list[RiskSubIssue] = []


class _ConflictsPayload(BaseModel):
    conflicts: list[CrossClauseConflict] = []


def run_batch_detector(
    client: RiskAgentClient,
    agent_name: str,
    batch_id: str,
    batch: list[ContractChunk],
    batch_text: str,
    global_terms_text: str = "",
) -> AgentAnalysisResult:
    valid_ids = {c.id for c in batch}
    system_prompt = (
        AGENT_1_SYSTEM_PROMPT if agent_name == "agent_1" else AGENT_2_SYSTEM_PROMPT
    )
    user_prompt = build_batch_prompt(
        agent_name=agent_name,
        batch_text=batch_text,
        global_terms_text=global_terms_text,
    )

    parsed = client.invoke_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        schema_cls=_BatchRisksPayload,
        fallback=_BatchRisksPayload(risks=[]),
    )

    filtered_risks: list[RiskCandidate] = []
    for item in parsed.risks:
        if item.chunk_id not in valid_ids:
            continue
        cleaned_subissues: list[RiskSubIssue] = []
        for sub in item.subissues:
            queries = [q.strip() for q in sub.search_queries if q and q.strip()][:3]
            cleaned_subissues.append(
                RiskSubIssue(
                    risk_type=sub.risk_type.strip() or item.risk_type,
                    description=sub.description.strip() or item.description,
                    legal_question=sub.legal_question.strip() or item.reason,
                    needs_web_search=bool(sub.needs_web_search) and bool(queries),
                    search_queries=queries,
                )
            )
        filtered_risks.append(
            RiskCandidate(
                chunk_id=item.chunk_id,
                risk_type=item.risk_type.strip(),
                description=item.description.strip(),
                severity=item.severity,
                reason=item.reason.strip(),
                subissues=cleaned_subissues,
            )
        )

    return AgentAnalysisResult(
        agent="agent_1" if agent_name == "agent_1" else "agent_2",
        batch_id=batch_id,
        risks=filtered_risks,
    )


def run_subissue_splitter(
    client: RiskAgentClient,
    candidate: MergedRiskCandidate,
    related_chunks: list[ContractChunk],
    global_terms_text: str = "",
) -> list[RiskSubIssue]:
    chunks_preview = "\n\n".join(
        f"[{c.id}] ({c.article or ''} {c.clause or ''}): {c.text[:1500]}"
        for c in related_chunks
    )
    prompt = f"""
THUẬT NGỮ ĐỊNH NGHĨA:
{global_terms_text or "Không có."}

ỨNG VIÊN RỦI RO:
- risk_type: {candidate.risk_type}
- description: {candidate.description}
- legal_question: {candidate.legal_question}
- search_queries: {candidate.search_queries}

ĐIỀU KHOẢN LIÊN QUAN:
{chunks_preview}
""".strip()

    fallback_sub = RiskSubIssue(
        risk_type=candidate.risk_type,
        description=candidate.description,
        legal_question=candidate.legal_question,
        needs_web_search=candidate.needs_web_search and bool(candidate.search_queries),
        search_queries=candidate.search_queries[:3],
    )
    parsed = client.invoke_json(
        system_prompt=AGENT_3_SPLIT_SYSTEM_PROMPT,
        user_prompt=prompt,
        schema_cls=_SplitSubissuesPayload,
        fallback=_SplitSubissuesPayload(subissues=[fallback_sub]),
    )
    if not parsed.subissues:
        return [fallback_sub]

    result: list[RiskSubIssue] = []
    for sub in parsed.subissues[:4]:
        queries = [q.strip() for q in sub.search_queries if q and q.strip()][:3]
        result.append(
            RiskSubIssue(
                risk_type=sub.risk_type.strip() or candidate.risk_type,
                description=sub.description.strip() or candidate.description,
                legal_question=sub.legal_question.strip() or candidate.legal_question,
                needs_web_search=bool(sub.needs_web_search) and bool(queries),
                search_queries=queries,
            )
        )
    return result or [fallback_sub]


def run_agent3_step(
    client: RiskAgentClient,
    candidate: MergedRiskCandidate,
    related_chunks: list[ContractChunk],
    legal_references: list[LegalReference],
    previous_reasoning: str = "",
    global_terms_text: str = "",
    can_search_more: bool = True,
) -> Agent3Decision:
    prompt = build_agent3_prompt(
        issue=candidate,
        contract_chunks=related_chunks,
        legal_references=legal_references,
        previous_reasoning=previous_reasoning,
        global_terms_text=global_terms_text,
    )
    fallback = Agent3Decision(
        action="final",
        reasoning="Không đủ căn cứ để kết luận mâu thuẫn pháp luật trực tiếp.",
        search_request=None,
        evidence_type="insufficient",
        confidence="low",
        analysis="Chưa có đủ tài liệu pháp luật đối chiếu trực tiếp với điều khoản.",
        conclusion="Cần rà soát thêm hoặc giữ nguyên để đàm phán thương mại.",
    )
    decision = client.invoke_json(
        system_prompt=AGENT_3_SYSTEM_PROMPT,
        user_prompt=prompt,
        schema_cls=Agent3Decision,
        fallback=fallback,
    )

    if decision.action == "search_legal" and (
        not can_search_more or decision.search_request is None
    ):
        return Agent3Decision(
            action="final",
            reasoning="Đã đạt giới hạn lượt tra cứu cho candidate này hoặc thiếu search_request.",
            search_request=None,
            evidence_type=(
                "insufficient"
                if decision.evidence_type == "direct_contradictory"
                else decision.evidence_type
            ),
            confidence=decision.confidence,
            analysis=decision.analysis or decision.reasoning,
            conclusion=decision.conclusion
            or "Chưa đủ căn cứ pháp luật kết luận trái luật.",
        )

    return decision


def run_cross_clause_auditor(
    client: RiskAgentClient,
    chunks: list[ContractChunk],
    candidates: list[MergedRiskCandidate],
    global_terms_text: str = "",
) -> list[CrossClauseConflict]:
    if len(chunks) < 2:
        return []

    compact_clauses = "\n".join(
        f"- [{c.id}] {c.article or ''} {c.clause or ''} ({c.hierarchy_path or ''}): {c.text[:450]}"
        for c in chunks[:40]
    )
    compact_issues = "\n".join(
        f"- {item.candidate_id} ({','.join(item.related_chunk_ids)}): {item.risk_type} - {item.description[:180]}"
        for item in candidates[:25]
    )
    prompt = f"""
THUẬT NGỮ ĐỊNH NGHĨA:
{global_terms_text or "Không có."}

DANH SÁCH ĐIỀU KHOẢN:
{compact_clauses}

CÁC VẤN ĐỀ ĐÃ PHÁT HIỆN:
{compact_issues or "Chưa có."}
""".strip()

    parsed = client.invoke_json(
        system_prompt=CROSS_CLAUSE_AUDITOR_SYSTEM_PROMPT,
        user_prompt=prompt,
        schema_cls=_ConflictsPayload,
        fallback=_ConflictsPayload(conflicts=[]),
    )

    normalized: list[CrossClauseConflict] = []
    for idx, c in enumerate(parsed.conflicts[:10], start=1):
        clauses = [cl.strip() for cl in c.involved_clauses if cl and cl.strip()]
        if len(clauses) < 2:
            continue
        normalized.append(
            CrossClauseConflict(
                conflict_id=c.conflict_id.strip() or f"CONF-{idx:02d}",
                involved_clauses=clauses,
                description=c.description.strip(),
                recommendation=c.recommendation.strip(),
            )
        )
    return normalized


def run_redline_generator(
    client: RiskAgentClient,
    risk_type: str,
    description: str,
    analysis: str,
    conclusion: str,
    related_chunks: list[ContractChunk],
) -> RedlineSuggestion:
    clause_text = "\n\n".join(
        f"[{c.id}] {c.article or ''} {c.clause or ''}:\n{c.text[:1200]}"
        for c in related_chunks
    )
    prompt = f"""
LOẠI RỦI RO: {risk_type}
MÔ TẢ: {description}
PHÂN TÍCH: {analysis}
KẾT LUẬN: {conclusion}

ĐIỀU KHOẢN GỐC:
{clause_text or "Không có."}
""".strip()

    fallback = RedlineSuggestion(
        action="REVIEW",
        proposed_text="",
        reason="Cần rà soát lại ngôn ngữ điều khoản cho rõ ràng và cân bằng quyền/nghĩa vụ.",
    )
    return client.invoke_json(
        system_prompt=REDLINE_GENERATOR_SYSTEM_PROMPT,
        user_prompt=prompt,
        schema_cls=RedlineSuggestion,
        fallback=fallback,
    )