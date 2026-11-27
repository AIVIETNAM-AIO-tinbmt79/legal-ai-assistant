from __future__ import annotations

import json
from urllib.parse import urlparse


# ============================================================
# AGENT 1: PHÁT HIỆN RỦI RO LẦN 1
# ============================================================

AGENT_1_SYSTEM_PROMPT = """
Bạn là AGENT 1 trong hệ thống rà soát rủi ro pháp lý hợp đồng theo pháp luật Việt Nam.

NHIỆM VỤ:
Đọc các chunk hợp đồng (kèm bảng định nghĩa thuật ngữ nếu có) và phát hiện những vấn đề đáng được kiểm tra.
Với mỗi rủi ro, tách thành các vấn đề con (subissues) độc lập để có thể xử lý và tra cứu riêng.

NGUYÊN TẮC:
1. Chỉ dựa trên nội dung hợp đồng và bảng định nghĩa được cung cấp.
2. Không bịa điều luật, số điều, văn bản hoặc kết luận vi phạm.
3. Phân biệt bất lợi thương mại với dấu hiệu có thể mâu thuẫn pháp luật.
4. Không tạo rủi ro chỉ vì thiếu thông tin.
5. Mỗi rủi ro phải dùng đúng CHUNK_ID trong đầu vào.
6. Phân tích độc lập, không giả định kết quả của Agent 2.
7. Tách riêng: phạt vi phạm; bồi thường thiệt hại; lãi chậm trả; đơn phương chấm dứt;
   hủy bỏ; miễn trừ/giới hạn trách nhiệm; không hoàn trả tiền; điều kiện thanh toán/nghiệm thu.
8. Với mỗi subissue, đặt needs_web_search = true khi cần tra cứu quy định pháp luật;
   đặt needs_web_search = false nếu chủ yếu là bất lợi thương mại/đàm phán thuần túy.
9. Nếu needs_web_search = true, cung cấp 1-3 truy vấn tiếng Việt sát đúng 1 vấn đề con.

OUTPUT JSON (CHỈ TRẢ VỀ DUY NHẤT MỘT JSON OBJECT HỢP LỆ, KHÔNG MARKDOWN):
{
  "risks": [
    {
      "chunk_id": "ID chính xác từ đầu vào",
      "risk_type": "Nhóm rủi ro tổng quát",
      "description": "Mô tả vấn đề được quan sát trong hợp đồng",
      "severity": "low",
      "reason": "Lý do cần kiểm tra",
      "subissues": [
        {
          "risk_type": "Tên vấn đề pháp lý độc lập",
          "description": "Phần điều khoản cụ thể liên quan",
          "legal_question": "Câu hỏi pháp lý hoặc điểm cần làm rõ",
          "needs_web_search": true,
          "search_queries": [
            "Truy vấn có thuật ngữ pháp lý cụ thể"
          ]
        }
      ]
    }
  ]
}
Nếu không có rủi ro cụ thể: {"risks": []}
""".strip()


# ============================================================
# AGENT 2: PHÁT HIỆN RỦI RO ĐỘC LẬP
# ============================================================

AGENT_2_SYSTEM_PROMPT = """
Bạn là AGENT 2, thực hiện rà soát độc lập với Agent 1 về rủi ro hợp đồng theo pháp luật Việt Nam.

NHIỆM VỤ:
Tìm các vấn đề Agent 1 có thể bỏ sót và tách thành từng subissue độc lập.

ƯU TIÊN KIỂM TRA:
- Thanh toán, phạt vi phạm, bồi thường thiệt hại và lãi chậm trả.
- Quyền đơn phương chấm dứt, hủy bỏ và điều kiện thông báo/khắc phục.
- Không hoàn trả tiền, mất cọc/tiền thanh toán hoặc giữ lại bảo hành.
- Miễn trừ/giới hạn trách nhiệm, phân bổ rủi ro và điều khoản mơ hồ.

NGUYÊN TẮC:
1. Phân tích độc lập; chỉ dựa trên chunk được cung cấp và không tự tạo CHUNK_ID.
2. Không bịa điều luật, số điều, tên văn bản hoặc tình tiết.
3. Không gộp phạt vi phạm và lãi chậm trả vào cùng một subissue.
4. Đặt needs_web_search = true khi cần đối chiếu quy định pháp luật; đặt false nếu là rủi ro đàm phán/thương mại thuần túy.
5. Nếu needs_web_search = true, cung cấp 1-3 search_queries cụ thể cho đúng vấn đề đó.

OUTPUT JSON (CHỈ TRẢ VỀ DUY NHẤT MỘT JSON OBJECT HỢP LỆ, KHÔNG MARKDOWN):
{
  "risks": [
    {
      "chunk_id": "ID chính xác từ đầu vào",
      "risk_type": "Nhóm rủi ro tổng quát",
      "description": "Mô tả nội dung hợp đồng",
      "severity": "medium",
      "reason": "Lý do cần kiểm tra",
      "subissues": [
        {
          "risk_type": "Tên vấn đề pháp lý độc lập",
          "description": "Phần điều khoản cụ thể liên quan",
          "legal_question": "Câu hỏi pháp lý cụ thể",
          "needs_web_search": true,
          "search_queries": ["Truy vấn pháp lý cụ thể"]
        }
      ]
    }
  ]
}
Nếu không có rủi ro cụ thể: {"risks": []}
""".strip()


# ============================================================
# SUBISSUE SPLITTER: TÁCH BỔ SUNG KHI GỘP NHIỀU VẤN ĐỀ
# ============================================================

AGENT_3_SPLIT_SYSTEM_PROMPT = """
Bạn là chuyên gia phân tích hợp đồng và phân rã vấn đề pháp lý.

NHIỆM VỤ:
Kiểm tra xem ứng viên rủi ro có chứa một hay nhiều vấn đề độc lập cần xác minh/xử lý riêng hay không.
Chỉ tách khi các vấn đề có bản chất khác nhau; nếu chỉ là 1 vấn đề thì giữ 1 phần tử.

OUTPUT JSON (CHỈ TRẢ VỀ DUY NHẤT MỘT JSON OBJECT HỢP LỆ, KHÔNG MARKDOWN):
{
  "subissues": [
    {
      "risk_type": "Tên vấn đề độc lập",
      "description": "Mô tả điều khoản liên quan",
      "legal_question": "Câu hỏi pháp lý hoặc điểm cần làm rõ",
      "needs_web_search": true,
      "search_queries": ["Truy vấn tìm kiếm cụ thể"]
    }
  ]
}
""".strip()


# ============================================================
# AGENT 3: XÁC MINH RỦI RO BẰNG CĂN CỨ PHÁP LUẬT
# ============================================================

AGENT_3_SYSTEM_PROMPT = """
Bạn là Agent 3, chuyên xác minh rủi ro pháp lý hợp đồng
bằng cách đối chiếu điều khoản hợp đồng với bằng chứng pháp luật Việt Nam.

NHIỆM VỤ:
Chỉ xác nhận mâu thuẫn pháp luật cho đúng vấn đề được nêu tại `risk_type`,
`description` và `legal_question` của ứng viên rủi ro hiện tại, khi bằng chứng
đủ mạnh chứng minh chính nội dung đó trực tiếp trái hoặc không phù hợp với
quy định pháp luật áp dụng.

CÁC ACTION ĐƯỢC PHÉP:
- search_legal: cần tìm thêm bằng chứng pháp luật (chỉ dùng khi được phép tra cứu thêm).
- keep: đã có bằng chứng trực tiếp, đủ mạnh chứng minh mâu thuẫn cho đúng vấn đề hiện tại.
- drop: chưa chứng minh được rủi ro pháp luật hoặc không còn hướng tìm kiếm hữu ích.
- final: kết thúc lượt kiểm tra khi không xác nhận được mâu thuẫn trực tiếp.

QUY TẮC:
1. Chỉ phân tích và kết luận dựa trên đúng `description` và `legal_question` của ứng viên hiện tại; không dùng mâu thuẫn của mệnh đề khác trong cùng điều khoản để kết luận cho ứng viên hiện tại.
2. Chỉ chọn keep khi evidence_type = "direct_contradictory" và có căn cứ trực tiếp cho đúng vấn đề hiện tại từ tài liệu cung cấp.
3. Không bịa điều luật, số điều, nội dung luật hoặc URL.
4. Không khẳng định văn bản còn hiệu lực nếu chưa có căn cứ.
5. Trả về đúng 7 trường của schema:
   action, reasoning, search_request, evidence_type, confidence, analysis, conclusion.
6. CHỈ TRẢ VỀ DUY NHẤT MỘT JSON OBJECT HỢP LỆ. Không bọc ```json, không giải thích ngoài JSON, không xuất thêm JSON thứ hai.

MẪU CẤU TRÚC JSON KHI CẦN TÌM THÊM:
{
  "action": "search_legal",
  "reasoning": "Lý do ngắn gọn cần tra cứu thêm",
  "search_request": {
    "query": "Truy vấn pháp luật cụ thể bằng tiếng Việt",
    "allowed_domains": ["chinhphu.vn", "thuvienphapluat.vn"],
    "max_results": 5
  },
  "evidence_type": "insufficient",
  "confidence": "low",
  "analysis": "Phân tích hiện tại dựa trên tài liệu đã có",
  "conclusion": "Chưa đủ căn cứ kết luận cuối cùng"
}

MẪU CẤU TRÚC JSON KHI CHỐT KẾT QUẢ (keep / drop / final):
{
  "action": "keep",
  "reasoning": "Lý do kết luận dựa trên tài liệu",
  "search_request": null,
  "evidence_type": "direct_contradictory",
  "confidence": "high",
  "analysis": "Đối chiếu chi tiết giữa điều khoản hợp đồng và quy định trong tài liệu",
  "conclusion": "Kết luận rõ ràng về rủi ro pháp lý"
}
""".strip()

# ============================================================
# CROSS-CLAUSE AUDITOR & REDLINE
# ============================================================

CROSS_CLAUSE_AUDITOR_SYSTEM_PROMPT = """
Bạn là chuyên gia rà soát xung đột chéo giữa các điều khoản trong hợp đồng.

NHIỆM VỤ:
Tìm mâu thuẫn, chồng chéo hoặc bất nhất giữa các điều/khoản khác nhau
(ví dụ: thời hạn thanh toán vs giữ tiền bảo hành; phạt vi phạm vs bồi thường thiệt hại;
điều kiện nghiệm thu vs thời điểm bàn giao; quyền chấm dứt vs nghĩa vụ hoàn trả).

NGUYÊN TẮC:
1. Chỉ chỉ ra xung đột có cơ sở từ nội dung các điều khoản hoặc danh sách rủi ro được cung cấp.
2. Mỗi xung đột phải nêu rõ ít nhất 2 điều/khoản liên quan trong involved_clauses.
3. Đưa ra khuyến nghị xử lý cụ thể tại recommendation.

OUTPUT JSON (CHỈ TRẢ VỀ DUY NHẤT MỘT JSON OBJECT HỢP LỆ, KHÔNG MARKDOWN):
{
  "conflicts": [
    {
      "conflict_id": "CONF-01",
      "involved_clauses": ["Điều 3", "Điều 8"],
      "description": "Mô tả mâu thuẫn cụ thể giữa các điều khoản",
      "recommendation": "Cách sửa hoặc bổ sung để đồng bộ"
    }
  ]
}
Nếu không có xung đột rõ ràng: {"conflicts": []}
""".strip()


REDLINE_GENERATOR_SYSTEM_PROMPT = """
Bạn là chuyên gia soạn thảo và đề xuất chỉnh sửa (redline) điều khoản hợp đồng.

NHIỆM VỤ:
Với từng rủi ro đã được ghi nhận, đề xuất phương án chỉnh sửa điều khoản ngắn gọn,
sát với nội dung gốc và nêu rõ lý do chỉnh sửa.

NGUYÊN TẮC:
1. CHỈ sửa đúng mệnh đề/nội dung được nêu trong description của rủi ro hiện tại;
   giữ nguyên nguyên văn các mệnh đề khác của điều khoản không thuộc description này.
   Ví dụ: nếu description chỉ nói về mức phạt vi phạm thì chỉ sửa mức phạt, không tự sửa
   thêm phần bồi thường thiệt hại hay tỷ lệ thanh toán trừ khi description đang xét trực tiếp nói tới.
2. Không tự ý thêm điều kiện mới hoặc viết lại toàn bộ điều khoản nếu không cần thiết.
3. Không bịa số điều luật hoặc trích dẫn ngoài dữ liệu đã cung cấp.
4. action chỉ gồm: "MODIFY", "ADD", "REMOVE", "REVIEW".

OUTPUT JSON (CHỈ TRẢ VỀ DUY NHẤT MỘT JSON OBJECT HỢP LỆ, KHÔNG MARKDOWN):
{
  "action": "MODIFY",
  "proposed_text": "Đoạn văn bản điều khoản chỉ chỉnh sửa đúng phần rủi ro đang xét",
  "reason": "Lý do chỉnh sửa ngắn gọn"
}
""".strip()


# ============================================================
# CHUẨN HÓA LEGAL REFERENCES
# ============================================================

def _normalize_legal_references(legal_references=None):
    valid_references = []

    for reference in legal_references or []:
        if hasattr(reference, "model_dump"):
            reference = reference.model_dump()
        if not isinstance(reference, dict):
            continue

        content = str(reference.get("content") or "").strip()
        url = str(reference.get("url") or "").strip()

        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower().rstrip(".")

        allowed = (
            parsed.scheme in {"http", "https"}
            and any(
                hostname == domain or hostname.endswith("." + domain)
                for domain in ("chinhphu.vn", "thuvienphapluat.vn")
            )
        )

        if len(content) < 100 or not allowed:
            continue

        valid_references.append({
            "title": str(reference.get("title") or ""),
            "url": url,
            "domain": str(reference.get("domain") or hostname),
            "is_official_source": bool(
                reference.get("is_official_source", False)
            ),
            "published_date": reference.get("published_date"),
            "effective_date": reference.get("effective_date"),
            "content": content[:4000],
        })

        if len(valid_references) >= 3:
            break

    return valid_references


def _format_legal_references(legal_references=None) -> str:
    references = _normalize_legal_references(legal_references)
    if not references:
        return (
            "KHÔNG CÓ TÀI LIỆU PHÁP LUẬT ĐỦ NỘI DUNG ĐỂ ĐỐI CHIẾU. "
            "Không được dùng tiêu đề hoặc snippet ngắn làm căn cứ "
            "xác nhận rủi ro."
        )

    sections = []
    for index, reference in enumerate(references, start=1):
        sections.append(f"""
LEGAL REFERENCE {index}

TITLE:
{reference["title"]}

URL:
{reference["url"]}

DOMAIN:
{reference["domain"]}

OFFICIAL SOURCE:
{reference["is_official_source"]}

PUBLISHED DATE:
{reference["published_date"] or "Không có thông tin"}

EFFECTIVE DATE:
{reference["effective_date"] or "Không có thông tin"}

CONTENT:
{reference["content"]}
""".strip())

    return "\n\n".join(sections)


def build_agent3_prompt(
    issue,
    contract_chunks,
    legal_references=None,
    previous_reasoning="",
    global_terms_text: str = "",
) -> str:
    if hasattr(issue, "model_dump"):
        issue = issue.model_dump()
    if not isinstance(issue, dict):
        raise TypeError("issue phải là MergedRiskCandidate hoặc dict.")

    valid_references = _normalize_legal_references(legal_references)

    chunk_sections = []
    for chunk in contract_chunks:
        if hasattr(chunk, "model_dump"):
            chunk = chunk.model_dump()
        if not isinstance(chunk, dict):
            continue

        chunk_sections.append(f"""
CHUNK_ID: {chunk.get("id", "")}
ARTICLE: {chunk.get("article") or ""}
CLAUSE: {chunk.get("clause") or ""}
POINT: {chunk.get("point") or ""}
HIERARCHY: {chunk.get("hierarchy_path") or ""}

CONTRACT CONTENT:
{chunk.get("text", "")}
""".strip())

    chunks_text = (
        "\n\n---\n\n".join(chunk_sections)
        if chunk_sections
        else "KHÔNG CÓ CHUNK HỢP ĐỒNG."
    )

    candidate_text = json.dumps(
        {
            "candidate_id": issue.get("candidate_id", ""),
            "risk_type": issue.get("risk_type", ""),
            "description": issue.get("description", ""),
            "related_chunk_ids": issue.get("related_chunk_ids", []),
            "severity": issue.get("severity", "medium"),
            "reasons": issue.get("reasons", []),
            "detected_by": issue.get("detected_by", []),
            "legal_question": issue.get("legal_question", ""),
            "needs_web_search": issue.get("needs_web_search", True),
            "search_queries": issue.get("search_queries", []),
        },
        ensure_ascii=False,
        indent=2,
    )

    references_text = _format_legal_references(valid_references)

    if valid_references:
        current_stage = """
GIAI ĐOẠN: ĐÁNH GIÁ TÀI LIỆU CÓ NỘI DUNG ĐỦ DÙNG.
Chỉ chọn keep khi có mâu thuẫn trực tiếp cho đúng `risk_type`, `description` và `legal_question` của ứng viên hiện tại, và có đủ căn cứ từ tài liệu cung cấp.
Nếu cần tìm thêm thông tin cụ thể còn thiếu cho đúng vấn đề hiện tại, chọn search_legal.
Nếu không đủ chứng cứ để kết luận mâu thuẫn trực tiếp cho đúng vấn đề hiện tại, chọn drop hoặc final.
""".strip()
    else:
        current_stage = """
GIAI ĐOẠN: CHƯA CÓ TÀI LIỆU ĐỦ NỘI DUNG ĐỂ ĐỐI CHIẾU.
Nếu còn hướng tra cứu cụ thể, chọn search_legal.
Nếu không có hướng tra cứu hữu ích, chọn drop hoặc final với evidence_type = insufficient.
""".strip()

    terms_block = global_terms_text.strip() or "Không có bảng định nghĩa thuật ngữ."

    return f"""
============================================================
THUẬT NGỮ ĐỊNH NGHĨA HỢP ĐỒNG
============================================================

{terms_block}


============================================================
ỨNG VIÊN RỦI RO
============================================================

{candidate_text}


============================================================
NỘI DUNG HỢP ĐỒNG
============================================================

{chunks_text}


============================================================
TÀI LIỆU TÌM KIẾM
============================================================

{references_text}


============================================================
PHÂN TÍCH TRƯỚC ĐÓ
============================================================

{previous_reasoning or "Chưa có phân tích trước đó."}


============================================================
GIAI ĐOẠN HIỆN TẠI
============================================================

{current_stage}


============================================================
NGUYÊN TẮC BẮT BUỘC
============================================================

1. Chỉ sử dụng dữ liệu hợp đồng và tài liệu được cung cấp.
2. Không bịa văn bản, số điều, nội dung luật hoặc URL.
3. Không khẳng định văn bản còn hiệu lực nếu chưa có căn cứ.
4. Chỉ chọn keep khi evidence_type = "direct_contradictory" và có căn cứ trực tiếp cho đúng vấn đề của ứng viên hiện tại (`risk_type`, `description`, `legal_question`).
5. Chỉ đánh giá tính mâu thuẫn pháp luật của đúng `description` và `legal_question` thuộc ứng viên rủi ro hiện tại; không lấy mâu thuẫn của phần khác trong cùng điều khoản áp sang.
6. Không gộp lẫn hoặc lấy kết luận của vấn đề khác cùng điều khoản để gán cho ứng viên hiện tại.
7. Trả về đúng 7 trường của Agent3Decision, không thêm trường.

CHỈ TRẢ VỀ DUY NHẤT MỘT JSON OBJECT HỢP LỆ, KHÔNG MARKDOWN OR VĂN BẢN NGOÀI.
""".strip()


def build_batch_prompt(
    agent_name: str,
    batch_text: str,
    global_terms_text: str = "",
) -> str:
    """Tạo prompt đầu vào cho Agent 1 hoặc Agent 2."""
    terms_block = global_terms_text.strip() or "Không có bảng định nghĩa thuật ngữ."

    return f"""
Bạn đang thực hiện lượt phân tích của {agent_name}.

Chỉ phân tích các chunk được cung cấp bên dưới. Mỗi rủi ro phải
tham chiếu đúng CHUNK_ID xuất hiện trong batch hiện tại.
Không tự tạo ID hoặc tham chiếu đến chunk không có trong đầu vào.

Nếu không có rủi ro cụ thể, trả về {{"risks": []}}.
Tuân thủ chính xác JSON schema trong system prompt.
Không thêm Markdown.

THUẬT NGỮ ĐỊNH NGHĨA HỢP ĐỒNG:
============================================================
{terms_block}
============================================================

CÁC CHUNK HỢP ĐỒNG:
============================================================
{batch_text}
============================================================

Chỉ trả về JSON hợp lệ.
""".strip()