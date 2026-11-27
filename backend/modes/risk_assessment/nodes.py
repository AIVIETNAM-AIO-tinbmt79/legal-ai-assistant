from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any

from .agent import (
    MAX_AGENT3_SEARCH_CALLS,
    MAX_AGENT3_STEPS,
    RiskAgentClient,
    run_agent3_step,
    run_batch_detector,
    run_cross_clause_auditor,
    run_redline_generator,
    run_subissue_splitter,
)
from .chunker import (
    create_batches,
    extract_global_terms_map,
    format_batch,
    format_terms_map,
)
from .legal_tools import legal_search
from .schemas import (
    Agent3Decision,
    AgentAnalysisResult,
    AgentTrace,
    ContractChunk,
    CrossClauseConflict,
    FinalRiskAssessment,
    LegalReference,
    LegalSearchRequest,
    MergedRiskCandidate,
    RiskAssessmentState,
    RiskLevel,
    VerifiedRisk,
)

logger = logging.getLogger(__name__)

MAX_TOTAL_SEARCH_CALLS_PER_RUN = 16
MAX_REDLINE_ITEMS = 12
MAX_REFERENCE_CONTENT_CHARS = 700
MAX_REFERENCE_SNIPPET_CHARS = 300

def _clean_text_for_compare(text: str) -> str:
    return " ".join((text or "").split()).strip().lower()


def _compact_snippet(snippet: str, content: str, max_chars: int = MAX_REFERENCE_SNIPPET_CHARS) -> str:
    clean_snip = " ".join((snippet or "").split()).strip()
    clean_cont = _clean_text_for_compare(content)

    if not clean_snip:
        return ""

    # Nếu snippet nằm ngay trong phần đầu content thì không cần giữ lặp dài
    if clean_cont and clean_snip.lower() in clean_cont[: max_chars * 2]:
        if len(clean_snip) <= 160:
            return clean_snip
        return clean_snip[:157].rstrip() + "..."

    if len(clean_snip) > max_chars:
        return clean_snip[: max_chars - 3].rstrip() + "..."

    return clean_snip


def _get_client(state: RiskAssessmentState) -> RiskAgentClient:
    existing = state.get("_agent_client")  # type: ignore[typeddict-unknown-key]
    if isinstance(existing, RiskAgentClient):
        return existing
    return RiskAgentClient()


def _normalize_ascii_tokens(text: str) -> set[str]:
    norm = unicodedata.normalize("NFD", text or "")
    no_marks = "".join(ch for ch in norm if unicodedata.category(ch) != "Mn")
    cleaned = re.sub(r"[^\w\s]", " ", no_marks).lower()
    return {tok for tok in cleaned.split() if len(tok) > 1}


def _jaccard_similarity(a: str, b: str) -> float:
    set_a = _normalize_ascii_tokens(a)
    set_b = _normalize_ascii_tokens(b)
    if not set_a or not set_b:
        return 0.0
    union = set_a | set_b
    return len(set_a & set_b) / len(union) if union else 0.0


def _is_duplicate_issue(existing: dict[str, Any], candidate_item: dict[str, Any]) -> bool:
    type_sim = _jaccard_similarity(
        existing.get("risk_type", ""),
        candidate_item.get("risk_type", ""),
    )
    desc_sim = _jaccard_similarity(
        existing.get("description", ""),
        candidate_item.get("description", ""),
    )
    lq_sim = _jaccard_similarity(
        existing.get("legal_question", ""),
        candidate_item.get("legal_question", ""),
    )
    q_sim = _jaccard_similarity(
        " ".join(existing.get("search_queries") or []),
        " ".join(candidate_item.get("search_queries") or []),
    )

    # Khác hẳn loại rủi ro thì chỉ coi là trùng khi mô tả gần như giống hệt nhau
    if type_sim < 0.35:
        return desc_sim >= 0.85

    intent_sim = max(lq_sim, q_sim)
    if desc_sim >= 0.78:
        return True
    if desc_sim >= 0.55 and intent_sim >= 0.50:
        return True

    return False


def _dedup_merged_candidates(candidates: list[MergedRiskCandidate]) -> list[MergedRiskCandidate]:
    deduped: list[MergedRiskCandidate] = []
    for cand in candidates:
        cand_dict = {
            "description": cand.description,
            "legal_question": cand.legal_question,
            "search_queries": cand.search_queries,
        }
        matched_idx: int | None = None
        for idx, prev in enumerate(deduped):
            if set(prev.related_chunk_ids) != set(cand.related_chunk_ids):
                continue
            prev_dict = {
                "description": prev.description,
                "legal_question": prev.legal_question,
                "search_queries": prev.search_queries,
            }
            if _is_duplicate_issue(prev_dict, cand_dict):
                matched_idx = idx
                break

        if matched_idx is None:
            deduped.append(cand)
        else:
            prev = deduped[matched_idx]
            merged_reasons = list(prev.reasons)
            for r in cand.reasons:
                if r not in merged_reasons:
                    merged_reasons.append(r)

            merged_agents = list(prev.detected_by)
            for a in cand.detected_by:
                if a not in merged_agents:
                    merged_agents.append(a)

            merged_queries = list(prev.search_queries)
            for q in cand.search_queries:
                if q not in merged_queries and len(merged_queries) < 3:
                    merged_queries.append(q)

            deduped[matched_idx] = MergedRiskCandidate(
                candidate_id=prev.candidate_id,
                risk_type=prev.risk_type if len(prev.risk_type) >= len(cand.risk_type) else cand.risk_type,
                description=prev.description if len(prev.description) >= len(cand.description) else cand.description,
                related_chunk_ids=prev.related_chunk_ids,
                severity=_max_severity(prev.severity, cand.severity),
                reasons=merged_reasons,
                detected_by=merged_agents,
                legal_question=prev.legal_question or cand.legal_question,
                needs_web_search=prev.needs_web_search or cand.needs_web_search,
                search_queries=merged_queries,
            )

    return deduped


def prepare_batches_node(state: RiskAssessmentState) -> dict[str, Any]:
    chunks = state.get("chunks") or []
    terms_map = state.get("global_terms_map")
    if terms_map is None:
        terms_map = extract_global_terms_map(chunks)
    batches = state.get("batches") or create_batches(chunks)
    return {
        "global_terms_map": terms_map,
        "batches": batches,
    }


def make_batch_agent_node(agent_name: str):
    results_key = "agent_1_results" if agent_name == "agent_1" else "agent_2_results"

    def _node(state: RiskAssessmentState) -> dict[str, Any]:
        client = _get_client(state)
        terms_text = format_terms_map(state.get("global_terms_map"))
        batches = state.get("batches") or []
        collected: list[AgentAnalysisResult] = []

        for idx, batch in enumerate(batches):
            if client.remaining_calls() <= 2:
                logger.warning("[%s] Stop early due to LLM call budget", agent_name)
                break
            batch_id = f"{agent_name}_batch_{idx}"
            res = run_batch_detector(
                client=client,
                agent_name=agent_name,
                batch_id=batch_id,
                batch=batch,
                batch_text=format_batch(batch),
                global_terms_text=terms_text,
            )
            collected.append(res)

        return {results_key: collected}

    return _node


def _severity_rank(level: RiskLevel) -> int:
    return {"low": 1, "medium": 2, "high": 3}[level]


def _max_severity(a: RiskLevel, b: RiskLevel) -> RiskLevel:
    return a if _severity_rank(a) >= _severity_rank(b) else b


def merge_and_split_node(state: RiskAssessmentState) -> dict[str, Any]:
    client = _get_client(state)
    terms_text = format_terms_map(state.get("global_terms_map"))
    chunk_map = {c.id: c for c in (state.get("chunks") or [])}

    all_results: list[AgentAnalysisResult] = [
        *(state.get("agent_1_results") or []),
        *(state.get("agent_2_results") or []),
    ]

    grouped_by_chunk: dict[str, list[dict[str, Any]]] = {}

    for res in all_results:
        for risk in res.risks:
            subissues = risk.subissues or []
            if not subissues:
                fallback_q = (
                    f"{risk.risk_type} {risk.description}".strip()[:120]
                    or risk.reason.strip()[:120]
                )
                subissues = [
                    type(
                        "TmpSub",
                        (),
                        {
                            "risk_type": risk.risk_type,
                            "description": risk.description,
                            "legal_question": risk.reason or risk.description,
                            "needs_web_search": True,
                            "search_queries": [fallback_q] if fallback_q else [],
                        },
                    )()
                ]

            for sub in subissues:
                sub_type = (sub.risk_type or risk.risk_type).strip()
                sub_desc = (sub.description or risk.description).strip()
                sub_q = (sub.legal_question or risk.reason or sub_desc).strip()
                sub_queries = [q.strip() for q in (sub.search_queries or []) if q and q.strip()]
                if not sub_queries and (sub_q or sub_desc):
                    sub_queries = [(sub_q or sub_desc)[:120]]

                item_payload: dict[str, Any] = {
                    "chunk_ids": [risk.chunk_id],
                    "risk_type": sub_type,
                    "description": sub_desc,
                    "severity": risk.severity,
                    "reasons": [risk.reason.strip()] if risk.reason.strip() else [],
                    "detected_by": [res.agent],
                    "legal_question": sub_q,
                    "needs_web_search": bool(sub.needs_web_search) or bool(sub_queries),
                    "search_queries": sub_queries,
                }

                bucket_list = grouped_by_chunk.setdefault(risk.chunk_id, [])
                matched: dict[str, Any] | None = None
                for existing in bucket_list:
                    if _is_duplicate_issue(existing, item_payload):
                        matched = existing
                        break

                if matched is None:
                    bucket_list.append(item_payload)
                else:
                    matched["severity"] = _max_severity(matched["severity"], risk.severity)
                    if risk.reason.strip() and risk.reason.strip() not in matched["reasons"]:
                        matched["reasons"].append(risk.reason.strip())
                    if res.agent not in matched["detected_by"]:
                        matched["detected_by"].append(res.agent)
                    matched["needs_web_search"] = matched["needs_web_search"] or item_payload["needs_web_search"]
                    for q in sub_queries:
                        if q not in matched["search_queries"] and len(matched["search_queries"]) < 4:
                            matched["search_queries"].append(q)

    merged_list: list[MergedRiskCandidate] = []
    counter = 0

    for cid, items in grouped_by_chunk.items():
        for item in items:
            counter += 1
            candidate = MergedRiskCandidate(
                candidate_id=f"CAND-{counter:03d}",
                risk_type=item["risk_type"],
                description=item["description"],
                related_chunk_ids=item["chunk_ids"],
                severity=item["severity"],
                reasons=item["reasons"],
                detected_by=item["detected_by"],
                legal_question=item["legal_question"],
                needs_web_search=item["needs_web_search"],
                search_queries=item["search_queries"][:3],
            )

            looks_compound = any(tok in candidate.risk_type for tok in ("/", ";", " và ", " & "))
            if looks_compound and client.remaining_calls() > 4:
                related = [chunk_map[x] for x in candidate.related_chunk_ids if x in chunk_map]
                split_subs = run_subissue_splitter(
                    client=client,
                    candidate=candidate,
                    related_chunks=related,
                    global_terms_text=terms_text,
                )
                if len(split_subs) > 1:
                    for s_idx, sub in enumerate(split_subs, start=1):
                        s_queries = [q.strip() for q in (sub.search_queries or []) if q and q.strip()]
                        if not s_queries:
                            s_queries = [(sub.legal_question or sub.description)[:120]]
                        merged_list.append(
                            MergedRiskCandidate(
                                candidate_id=f"{candidate.candidate_id}-{s_idx}",
                                risk_type=sub.risk_type,
                                description=sub.description,
                                related_chunk_ids=candidate.related_chunk_ids,
                                severity=candidate.severity,
                                reasons=candidate.reasons,
                                detected_by=candidate.detected_by,
                                legal_question=sub.legal_question,
                                needs_web_search=sub.needs_web_search or bool(s_queries),
                                search_queries=s_queries[:3],
                            )
                        )
                    continue

            merged_list.append(candidate)

    final_candidates = _dedup_merged_candidates(merged_list)
    return {"candidate_issues": final_candidates}


def _dedup_references(refs: list[LegalReference]) -> list[LegalReference]:
    seen: set[str] = set()
    out: list[LegalReference] = []
    for r in refs:
        key = r.url.strip() or r.title.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def _filter_context_relevant_refs(
    refs: list[LegalReference],
    contract_summary: str,
    chunks: list[ContractChunk],
) -> list[LegalReference]:
    if len(refs) <= 1:
        return refs

    context_tokens = _normalize_ascii_tokens(
        f"{contract_summary} " + " ".join(c.text[:200] for c in chunks[:4])
    )
    contract_is_labor = (
        "lao" in context_tokens and ("dong" in context_tokens or "luat" in context_tokens)
    )
    if contract_is_labor:
        return refs

    non_labor: list[LegalReference] = []
    for r in refs:
        blob_tokens = _normalize_ascii_tokens(f"{r.title} {r.snippet} {r.content[:400]}")
        is_labor_ref = (
            "lao" in blob_tokens and ("dong" in blob_tokens or "luat" in blob_tokens)
        )
        if not is_labor_ref:
            non_labor.append(r)

    return non_labor if non_labor else refs


def _compact_references(
    refs: list[LegalReference],
    max_items: int = 3,
    max_content_chars: int = MAX_REFERENCE_CONTENT_CHARS,
    max_snippet_chars: int = MAX_REFERENCE_SNIPPET_CHARS,
) -> list[LegalReference]:
    compacted: list[LegalReference] = []
    for r in refs[:max_items]:
        content = r.content or ""
        if len(content) > max_content_chars:
            content = content[: max_content_chars - 3].rstrip() + "..."

        snippet = _compact_snippet(
            snippet=r.snippet or "",
            content=content,
            max_chars=max_snippet_chars,
        )

        compacted.append(
            LegalReference(
                title=r.title,
                url=r.url,
                snippet=snippet,
                content=content,
                domain=r.domain,
                published_date=r.published_date,
                effective_date=r.effective_date,
                is_official_source=r.is_official_source,
            )
        )
    return compacted


def verify_and_audit_node(state: RiskAssessmentState) -> dict[str, Any]:
    client = _get_client(state)
    terms_text = format_terms_map(state.get("global_terms_map"))
    all_chunks = state.get("chunks") or []
    chunk_map = {c.id: c for c in all_chunks}
    contract_summary = state.get("contract_summary") or ""
    candidates = state.get("candidate_issues") or []

    verified: list[VerifiedRisk] = []
    traces: list[AgentTrace] = []
    total_search_calls = 0
    step_counter = 0

    for cand in candidates:
        related_chunks: list[ContractChunk] = [
            chunk_map[cid] for cid in cand.related_chunk_ids if cid in chunk_map
        ]
        if not related_chunks:
            continue

        refs: list[LegalReference] = []
        cand_search_calls = 0
        previous_reasoning = ""
        final_decision: Agent3Decision | None = None

        if (
            cand.needs_web_search
            and cand.search_queries
            and cand_search_calls < MAX_AGENT3_SEARCH_CALLS
            and total_search_calls < MAX_TOTAL_SEARCH_CALLS_PER_RUN
        ):
            for q in cand.search_queries[:2]:
                if (
                    cand_search_calls >= MAX_AGENT3_SEARCH_CALLS
                    or total_search_calls >= MAX_TOTAL_SEARCH_CALLS_PER_RUN
                ):
                    break
                search_res = legal_search(LegalSearchRequest(query=q, max_results=3))
                cand_search_calls += 1
                total_search_calls += 1
                refs = _filter_context_relevant_refs(
                    _dedup_references(refs + search_res.references),
                    contract_summary=contract_summary,
                    chunks=all_chunks,
                )
                step_counter += 1
                traces.append(
                    AgentTrace(
                        step=step_counter,
                        action="initial_search",
                        reasoning=f"Tra cứu ban đầu cho {cand.candidate_id}",
                        candidate_id=cand.candidate_id,
                        tool_query=q,
                        references_found=len(refs),
                    )
                )

        for _ in range(MAX_AGENT3_STEPS):
            if client.remaining_calls() <= 2:
                break
            can_search_more = (
                cand_search_calls < MAX_AGENT3_SEARCH_CALLS
                and total_search_calls < MAX_TOTAL_SEARCH_CALLS_PER_RUN
            )
            decision = run_agent3_step(
                client=client,
                candidate=cand,
                related_chunks=related_chunks,
                legal_references=refs,
                previous_reasoning=previous_reasoning,
                global_terms_text=terms_text,
                can_search_more=can_search_more,
            )
            previous_reasoning = decision.reasoning
            step_counter += 1

            if decision.action == "search_legal" and decision.search_request and can_search_more:
                req = LegalSearchRequest(
                    query=decision.search_request.query,
                    allowed_domains=decision.search_request.allowed_domains,
                    max_results=decision.search_request.max_results,
                )
                search_res = legal_search(req)
                cand_search_calls += 1
                total_search_calls += 1
                refs = _filter_context_relevant_refs(
                    _dedup_references(refs + search_res.references),
                    contract_summary=contract_summary,
                    chunks=all_chunks,
                )
                traces.append(
                    AgentTrace(
                        step=step_counter,
                        action="search_legal",
                        reasoning=decision.reasoning,
                        candidate_id=cand.candidate_id,
                        tool_query=req.query,
                        references_found=len(refs),
                    )
                )
                continue

            traces.append(
                AgentTrace(
                    step=step_counter,
                    action=decision.action,
                    reasoning=decision.reasoning,
                    candidate_id=cand.candidate_id,
                    references_found=len(refs),
                )
            )
            final_decision = decision
            break

        if final_decision and final_decision.action == "keep" and refs:
            redline = None
            if len(verified) < MAX_REDLINE_ITEMS and client.remaining_calls() > 1:
                redline = run_redline_generator(
                    client=client,
                    risk_type=cand.risk_type,
                    description=cand.description,
                    analysis=final_decision.analysis,
                    conclusion=final_decision.conclusion,
                    related_chunks=related_chunks,
                )

            verified.append(
                VerifiedRisk(
                    candidate_id=cand.candidate_id,
                    risk_type=cand.risk_type,
                    description=cand.description,
                    contract_chunk_ids=cand.related_chunk_ids,
                    severity=cand.severity,
                    legal_references=_compact_references(refs, max_items=3),
                    evidence_type="direct_contradictory",
                    confidence=final_decision.confidence,
                    analysis=final_decision.analysis or final_decision.reasoning,
                    conclusion=final_decision.conclusion or cand.description,
                    redline=redline,
                )
            )

    conflicts = []
    if client.remaining_calls() > 0:
        conflicts = run_cross_clause_auditor(
            client=client,
            chunks=all_chunks,
            candidates=candidates,
            global_terms_text=terms_text,
        )

    return {
        "verified_issues": verified,
        "agent_trace": traces,
        "agent3_tool_calls": total_search_calls,
        "cross_clause_conflicts": conflicts,
    }


def synthesize_report_node(state: RiskAssessmentState) -> dict[str, Any]:
    issues = state.get("verified_issues") or []
    conflicts = state.get("cross_clause_conflicts") or []

    overall_level: RiskLevel = "low"
    for issue in issues:
        overall_level = _max_severity(overall_level, issue.severity)
    if conflicts and overall_level == "low":
        overall_level = "medium"

    recommendations: list[str] = []
    for issue in issues:
        if issue.redline and issue.redline.proposed_text:
            recommendations.append(
                f"[{issue.candidate_id} - {issue.redline.action}] {issue.redline.proposed_text}"
            )
    for conf in conflicts:
        recommendations.append(
            f"[{conf.conflict_id} - {', '.join(conf.involved_clauses)}] {conf.recommendation}"
        )

    summary = (
        f"Phát hiện {len(issues)} rủi ro pháp lý được xác minh trực tiếp "
        f"và {len(conflicts)} xung đột chéo giữa các điều khoản."
    )

    assessment = FinalRiskAssessment(
        risk_level=overall_level,
        summary=summary,
        issues=issues,
        cross_clause_conflicts=conflicts,
        recommendations=recommendations,
    )
    return {"final_assessment": assessment}