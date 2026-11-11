import json
import os
import re
from typing import Any

from openai import OpenAI

from .legal_tools import legal_search, get_graph_schema_context
from .prompts import (
    AGENT_1_SYSTEM_PROMPT,
    AGENT_2_SYSTEM_PROMPT,
    AGENT_3_SYSTEM_PROMPT,
    build_agent3_prompt,
    build_batch_prompt,
)
from .schemas import (
    Agent3Decision,
    AgentIssue,
    BatchRiskResult,
    ContractChunk,
    LegalReference,
    LegalSearchRequest,
    Risk,
    VerifiedIssue,
)


FPT_BASE_URL = os.getenv(
    "LLM_BASE_URL",
    "https://mkp-api.fptcloud.com/v1",
)

FPT_API_KEY = os.getenv("LLM_API_KEY")

FPT_MODEL = os.getenv(
    "LLM_MODEL",
    "gemma-3-27b-it",
)

MAX_AGENT3_TOOL_CALLS_PER_ISSUE = int(
    os.getenv(
        "MAX_AGENT3_TOOL_CALLS_PER_ISSUE",
        "2",
    )
)


_client = None


def get_llm_client():
    global _client

    if _client is None:
        if not FPT_API_KEY:
            raise RuntimeError(
                "FPT_API_KEY chưa được cấu hình."
            )

        _client = OpenAI(
            api_key=FPT_API_KEY,
            base_url=FPT_BASE_URL,
        )

    return _client


def call_llm(
    system_prompt: str,
    user_prompt: str,
) -> str:
    response = get_llm_client().chat.completions.create(
        model=FPT_MODEL,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
    )

    return response.choices[0].message.content or ""


def parse_json(text: str) -> dict:
    text = (text or "").strip()

    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\s*```$",
        "",
        text,
    )

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")

        if start == -1 or end == -1:
            raise ValueError(
                "LLM không trả về JSON hợp lệ."
            )

        return json.loads(
            text[start:end + 1]
        )


def run_agent_1(
    batches: list[list[ContractChunk]],
) -> list[BatchRiskResult]:
    results = []

    for index, batch in enumerate(batches, start=1):
        prompt = build_batch_prompt(
            "AGENT 1",
            _format_batch(batch),
        )

        raw = call_llm(
            AGENT_1_SYSTEM_PROMPT,
            prompt,
        )

        data = parse_json(raw)

        risks = [
            Risk.model_validate(item)
            for item in data.get("risks", [])
        ]

        results.append(
            BatchRiskResult(
                agent="agent_1",
                batch_id=f"batch_{index}",
                risks=risks,
            )
        )

    return results


def run_agent_2(
    batches: list[list[ContractChunk]],
) -> list[BatchRiskResult]:
    results = []

    for index, batch in enumerate(batches, start=1):
        prompt = build_batch_prompt(
            "AGENT 2",
            _format_batch(batch),
        )

        raw = call_llm(
            AGENT_2_SYSTEM_PROMPT,
            prompt,
        )

        data = parse_json(raw)

        risks = [
            Risk.model_validate(item)
            for item in data.get("risks", [])
        ]

        results.append(
            BatchRiskResult(
                agent="agent_2",
                batch_id=f"batch_{index}",
                risks=risks,
            )
        )

    return results


def _format_batch(
    batch: list[ContractChunk],
) -> str:
    parts = []

    for chunk in batch:
        parts.append(
            f"""
CHUNK_ID: {chunk.id}
HIERARCHY: {chunk.hierarchy_path or ""}
ARTICLE: {chunk.article or ""}
CLAUSE: {chunk.clause or ""}
POINT: {chunk.point or ""}

CONTENT:
{chunk.text}
""".strip()
        )

    return "\n\n".join(parts)


def merge_agent_results(
    agent_1_results: list[BatchRiskResult],
    agent_2_results: list[BatchRiskResult],
) -> list[AgentIssue]:
    """
    Merge duplicate/similar candidates without requiring both agents
    to agree. Agent 3 is responsible for legal verification.
    """

    candidates = []

    for result in agent_1_results + agent_2_results:
        for risk in result.risks:
            candidates.append(risk)

    groups: dict[tuple[str, str], list[Risk]] = {}

    for risk in candidates:
        key = (
            risk.chunk_id,
            risk.risk_type.strip().lower(),
        )
        groups.setdefault(key, []).append(risk)

    issues = []

    for index, risks in enumerate(
        groups.values(),
        start=1,
    ):
        primary = max(
            risks,
            key=lambda item: {
                "high": 3,
                "medium": 2,
                "low": 1,
            }[item.severity],
        )

        reasons = " | ".join(
            dict.fromkeys(
                item.reason
                for item in risks
                if item.reason
            )
        )

        issues.append(
            AgentIssue(
                issue_id=f"issue_{index:04d}",
                risk_type=primary.risk_type,
                description=primary.description,
                related_chunk_ids=[primary.chunk_id],
                severity=primary.severity,
                legal_question=(
                    f"Quy định pháp luật nào điều chỉnh "
                    f"vấn đề '{primary.risk_type}' "
                    f"trong điều khoản này và điều khoản hợp đồng "
                    f"có mâu thuẫn trực tiếp với quy định đó không?"
                ),
            )
        )

    return issues

def _build_graph_context_phrases(issue, contract_chunks) -> list[str]:
    """Tạo các cụm ngắn để tìm Entity, tránh dùng cả đoạn dài làm phrase."""
    phrases = []
    seen = set()

    def add(value: str):
        value = re.sub(r"\s+", " ", str(value or "")).strip(" .,:;!?()[]{}\"'")
        if 3 <= len(value) <= 80 and value.lower() not in seen:
            seen.add(value.lower())
            phrases.append(value)

    add(issue.risk_type)
    for segment in re.split(r"[\n.;,:!?()]+", issue.description or ""):
        add(segment)

    # Entity text thường là cụm danh từ ngắn; tạo n-gram 2-4 từ từ hợp đồng.
    stop_words = {
        "và", "hoặc", "của", "cho", "trong", "được", "theo", "là",
        "các", "những", "một", "bên", "này", "đó", "khi", "nếu",
        "phải", "thì", "sẽ", "đã", "có", "không", "tại", "với",
    }
    for chunk in contract_chunks:
        words = re.findall(r"[\wÀ-ỹ]+", chunk.text.lower())
        useful = [word for word in words if word not in stop_words]
        for n in (2, 3, 4):
            for index in range(max(0, len(useful) - n + 1)):
                add(" ".join(useful[index:index + n]))
                if len(phrases) >= 35:
                    return phrases
    return phrases[:35]


def normalize_agent3_decision(
    data: dict,
    issue: AgentIssue | None = None,
) -> dict:
    """Chuẩn hóa output của LLM3 trước khi validate Pydantic."""

    data = dict(data)

    # Chuẩn hóa evidence_type
    evidence_type = data.get("evidence_type")

    if evidence_type is None or not str(evidence_type).strip():
        data["evidence_type"] = "insufficient"

    action = data.get("action")
    search_request = data.get("search_request")

    if action == "search_legal":
        # Nếu LLM không tạo search_request hợp lệ,
        # khởi tạo object tìm kiếm.
        if not isinstance(search_request, dict):
            search_request = {}

        query = search_request.get("query")

        # Bổ sung query từ câu hỏi pháp lý của candidate
        # nếu LLM bỏ trống hoặc không cung cấp query.
        if not isinstance(query, str) or not query.strip():
            if issue is None:
                raise ValueError(
                    "Agent 3 yêu cầu search_legal "
                    "nhưng thiếu search_request.query."
                )

            search_request["query"] = issue.legal_question

        data["search_request"] = search_request

    elif search_request == {}:
        # Những action không cần tìm kiếm pháp luật
        # không nên giữ một search_request rỗng.
        data["search_request"] = None

    return data


def run_agent_3_issue(
    issue: AgentIssue,
    contract_chunks: list[ContractChunk],
    trace: list[dict] | None = None,
) -> VerifiedIssue | None:
    relevant_chunks = [
        chunk
        for chunk in contract_chunks
        if chunk.id in issue.related_chunk_ids
    ]

    references: list[LegalReference] = []
    previous_reasoning = ""
    tool_calls = 0

    # Lấy schema thật và các entity/relationship liên quan đến candidate.
    # Agent 3 dùng context này để chọn type; không tự đoán schema.
    graph_context = get_graph_schema_context(
        search_phrases=_build_graph_context_phrases(
            issue,
            relevant_chunks,
        ),
    )

    for step in range(
        MAX_AGENT3_TOOL_CALLS_PER_ISSUE + 1
    ):
        prompt = build_agent3_prompt(
            issue=issue,
            contract_chunks=relevant_chunks,
            legal_references=references,
            previous_reasoning=previous_reasoning,
            graph_schema_context=graph_context,
        )

        raw = call_llm(
            AGENT_3_SYSTEM_PROMPT,
            prompt,
        )

        decision_data = parse_json(raw)

        decision = Agent3Decision.model_validate(
        normalize_agent3_decision(
        decision_data,
        issue=issue,
        )
    )

        previous_reasoning = decision.reasoning

        if trace is not None:
            trace.append(
                {
                    "step": step + 1,
                    "action": decision.action,
                    "reasoning": decision.reasoning,
                    "issue_id": issue.issue_id,
                    "tool_query": (
                        decision.search_request.query
                        if decision.search_request
                        else None
                    ),
                    "selected_relationship_types": (
                        decision.search_request.relationship_types
                        if decision.search_request
                        else []
                    ),
                    "references_found": len(references),
                    "graph_entity_types": graph_context.get("entity_types", []),
                    "graph_relationship_types": graph_context.get("relationship_types", []),
                    "graph_entities_found": len(graph_context.get("matched_entities", [])),
                    "graph_relationships_found": len(graph_context.get("matched_relationships", [])),
                }
            )

        if decision.action == "search_legal":
            if not decision.search_request:
                break

            if tool_calls >= MAX_AGENT3_TOOL_CALLS_PER_ISSUE:
                break

            search_request = decision.search_request

            tool_result = legal_search(
                query=search_request.query,
                search_phrases=search_request.search_phrases,
                entity_types=search_request.entity_types,
                relationship_types=search_request.relationship_types,
                top_k=search_request.top_k,
                relationship_top_k=10,
            )

            tool_calls += 1

            references = list(tool_result.references)
            continue

        if decision.action == "keep":
            # Agent 3 chỉ được giữ một risk khi chính nó xác định
            # rằng căn cứ pháp luật áp dụng trực tiếp và mâu thuẫn
            # với điều khoản hợp đồng. Không suy luận "có references"
            # => "vi phạm".
            if decision.evidence_type != "direct_contradictory":
                return None

            if not references:
                return None

            confidence = decision.legal_confidence
            if confidence not in {"low", "medium", "high"}:
                confidence = "low"

            return VerifiedIssue(
                issue_id=issue.issue_id,
                risk_type=issue.risk_type,
                description=issue.description,
                contract_chunk_ids=issue.related_chunk_ids,
                severity=issue.severity,
                legal_references=references,
                evidence_type="direct_contradictory",
                legal_confidence=confidence,
                analysis=decision.analysis,
                conclusion=decision.conclusion,
            )

        # drop / final
        return None

    return None


def run_agent_3(
    issues: list[AgentIssue],
    contract_chunks: list[ContractChunk],
    trace: list[dict] | None = None,
) -> list[VerifiedIssue]:
    verified = []

    for issue in issues:
        result = run_agent_3_issue(
            issue=issue,
            contract_chunks=contract_chunks,
            trace=trace,
        )

        if result is not None:
            verified.append(result)

    return verified
