from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Đảm bảo import được package backend khi chạy từ thư mục gốc hoặc backend/
CURRENT_DIR = Path(__file__).resolve().parent
for candidate_dir in (CURRENT_DIR, CURRENT_DIR.parent, CURRENT_DIR / "backend"):
    if str(candidate_dir) not in sys.path:
        sys.path.insert(0, str(candidate_dir))


def _field(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _short(text: Any, limit: int = 110) -> str:
    s = " ".join(str(text or "").split())
    return s if len(s) <= limit else s[: limit - 3] + "..."


def _load_sample_chunks():
    """
    Thử import hàm chunk có sẵn trong repo (nếu có),
    hoặc fallback sang đoạn hợp đồng mẫu nhiều ý trên cùng điều khoản để test nhanh.
    """
    try:
        from modes.risk_assessment.chunker import chunk_contract_text  # type: ignore

        sample_contract = """
Điều 3. Thanh toán, bảo hành và phạt vi phạm
1. Bên A thanh toán 100% giá trị hợp đồng ngay sau khi ký. Nếu Bên B giao trễ bất kỳ hạng mục nào quá 1 ngày, Bên B chịu phạt vi phạm 25% giá trị phần hợp đồng bị vi phạm và bồi thường toàn bộ thiệt hại phát sinh mà không có thỏa thuận giới hạn.
2. Bên A giữ lại 10% giá trị hợp đồng trong 24 tháng kể từ ngày nghiệm thu làm tiền bảo hành, không tính lãi, và thanh toán đợt cuối sau khi hoàn tất nghĩa vụ bảo hành.

Điều 6. Chấm dứt hợp đồng
1. Bên A có quyền đơn phương chấm dứt hợp đồng bất kỳ lúc nào không cần báo trước và không cần lý do; khi đó Bên B phải hoàn trả toàn bộ tiền đã nhận trong vòng 3 ngày làm việc.
""".strip()
        return chunk_contract_text(sample_contract)
    except Exception:
        from modes.risk_assessment.schemas import ContractChunk

        return [
            ContractChunk(
                id="chk_d3_1",
                text=(
                    "1. Bên A thanh toán 100% giá trị hợp đồng ngay sau khi ký. "
                    "Nếu Bên B giao trễ bất kỳ hạng mục nào quá 1 ngày, Bên B chịu phạt vi phạm "
                    "25% giá trị phần hợp đồng bị vi phạm và bồi thường toàn bộ thiệt hại phát sinh "
                    "mà không có thỏa thuận giới hạn."
                ),
                article="Điều 3",
                clause="Khoản 1",
                hierarchy_path="Điều 3 > Khoản 1",
                chunk_type="clause",
            ),
            ContractChunk(
                id="chk_d3_2",
                text=(
                    "2. Bên A giữ lại 10% giá trị hợp đồng trong 24 tháng kể từ ngày nghiệm thu "
                    "làm tiền bảo hành, không tính lãi, và thanh toán đợt cuối sau khi hoàn tất."
                ),
                article="Điều 3",
                clause="Khoản 2",
                hierarchy_path="Điều 3 > Khoản 2",
                chunk_type="clause",
            ),
            ContractChunk(
                id="chk_d6_1",
                text=(
                    "1. Bên A có quyền đơn phương chấm dứt hợp đồng bất kỳ lúc nào không cần báo trước "
                    "và không cần lý do; khi đó Bên B phải hoàn trả toàn bộ tiền đã nhận trong 3 ngày."
                ),
                article="Điều 6",
                clause="Khoản 1",
                hierarchy_path="Điều 6 > Khoản 1",
                chunk_type="clause",
            ),
        ]


def run_diagnostic() -> None:
    from modes.risk_assessment.workflow import build_risk_assessment_graph

    chunks = _load_sample_chunks()
    print(f"=== 1. CHUNKS LOADED: {len(chunks)} ===")
    for c in chunks:
        print(
            f"  - {_field(c, 'id')} ({_field(c, 'hierarchy_path') or _field(c, 'article')}): "
            f"{_short(_field(c, 'text'), 100)}"
        )

    graph = build_risk_assessment_graph()
    initial_state: dict[str, Any] = {
        "chunks": chunks,
        "global_terms_map": {},
        "contract_summary": "Hợp đồng cung cấp dịch vụ và hàng hóa mẫu để kiểm tra trace từng bước.",
    }

    accumulated_state: dict[str, Any] = dict(initial_state)
    printed_merge = False
    seen_traces = 0

    print("\n=== 2. STREAMING GRAPH TRACE ===")
    for event in graph.stream(initial_state, stream_mode="updates"):
        for node_name, patch in event.items():
            if not isinstance(patch, dict):
                continue

            for k, v in patch.items():
                if k in ("agent_1_results", "agent_2_results", "verified_issues", "agent_trace"):
                    prev = list(accumulated_state.get(k) or [])
                    if isinstance(v, list):
                        prev.extend(v)
                    accumulated_state[k] = prev
                elif k == "agent3_tool_calls":
                    accumulated_state[k] = int(accumulated_state.get(k) or 0) + int(v or 0)
                else:
                    accumulated_state[k] = v

            # Điểm 1: Sau merge_and_split
            if "candidate_issues" in patch and not printed_merge:
                printed_merge = True
                candidates = patch["candidate_issues"] or []
                print(f"\n[CHECKPOINT A - AFTER MERGE] Total candidates: {len(candidates)}")
                for cand in candidates:
                    cid = _field(cand, "candidate_id")
                    cids = _field(cand, "related_chunk_ids")
                    rtype = _field(cand, "risk_type")
                    desc = _field(cand, "description")
                    queries = _field(cand, "search_queries")
                    print(f"  * {cid} | chunks={cids} | type={rtype!r}")
                    print(f"      desc   : {_short(desc, 120)}")
                    print(f"      queries: {queries}")

            # Điểm 2: Từng bước agent_trace của Agent 3 / search
            traces = accumulated_state.get("agent_trace") or []
            if len(traces) > seen_traces:
                new_traces = traces[seen_traces:]
                seen_traces = len(traces)
                for tr in new_traces:
                    step = _field(tr, "step")
                    action = _field(tr, "action")
                    cand_id = _field(tr, "candidate_id")
                    t_query = _field(tr, "tool_query")
                    refs_cnt = _field(tr, "references_found")
                    reason = _field(tr, "reasoning")
                    print(
                        f"  [TRACE step={step} node={node_name}] cand={cand_id} "
                        f"action={action} refs={refs_cnt} query={t_query!r}"
                    )
                    if reason:
                        print(f"      reasoning: {_short(reason, 120)}")

    # Điểm 3: Đối chiếu trước / sau final_assessment
    print("\n=== 3. ISSUE ALIGNMENT CHECK (BEFORE vs AFTER FINAL_ASSESSMENT) ===")
    cand_map: dict[str, Any] = {}
    for cand in accumulated_state.get("candidate_issues") or []:
        cid = _field(cand, "candidate_id")
        cand_map[cid] = cand

    verified = accumulated_state.get("verified_issues") or []
    print(f"Verified issues count: {len(verified)}")
    for item in verified:
        cid = _field(item, "candidate_id")
        rtype = _field(item, "risk_type")
        desc = _field(item, "description")
        ev_type = _field(item, "evidence_type")
        conf = _field(item, "confidence")
        concl = _field(item, "conclusion")
        redline = _field(item, "redline")
        rl_action = _field(redline, "action")
        rl_text = _field(redline, "proposed_text")

        orig_cand = cand_map.get(cid)
        orig_queries = _field(orig_cand, "search_queries")

        print(f"  - {cid} | type={rtype!r} | evidence={ev_type} | conf={conf}")
        print(f"      orig_queries : {orig_queries}")
        print(f"      description  : {_short(desc, 120)}")
        print(f"      conclusion   : {_short(concl, 140)}")
        if redline:
            print(f"      redline [{rl_action}]: {_short(rl_text, 120)}")

    final_assessment = accumulated_state.get("final_assessment")
    if final_assessment is not None:
        dump = (
            final_assessment.model_dump()
            if hasattr(final_assessment, "model_dump")
            else final_assessment
        )
        out_path = CURRENT_DIR / "debug_final_assessment.json"
        out_path.write_text(json.dumps(dump, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nSaved full final_assessment to: {out_path}")


if __name__ == "__main__":
    run_diagnostic()