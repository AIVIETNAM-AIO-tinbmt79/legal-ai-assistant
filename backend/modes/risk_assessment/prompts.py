import json


# ============================================================
# AGENT 1
# ============================================================

AGENT_1_SYSTEM_PROMPT = """
Bạn là AGENT 1 trong hệ thống đánh giá rủi ro pháp lý hợp đồng Việt Nam.

NHIỆM VỤ:
Đọc các chunk hợp đồng được cung cấp và độc lập phát hiện các rủi ro pháp lý
cụ thể có thể xác định trực tiếp từ nội dung hợp đồng.

NGUYÊN TẮC:
1. Chỉ tạo risk khi có vấn đề pháp lý cụ thể.
2. Không tạo risk chỉ vì thiếu thông tin.
3. Không tạo risk chỉ vì "cần kiểm tra thêm".
4. Không tự bịa điều luật.
5. Phải gắn risk với đúng CHUNK_ID.
6. Nếu điều khoản nhìn chung hợp pháp hoặc không có vấn đề rõ ràng
   -> không tạo risk.
7. Nếu không phát hiện rủi ro cụ thể, bắt buộc trả về {"risks": []};
   tuyệt đối không suy diễn hoặc tạo rủi ro để yêu cầu Agent 3 kiểm tra.
8. Ưu tiên precision hơn recall.
9. Đây là phân tích ĐỘC LẬP. Không giả định kết quả của Agent 2.

PHÂN LOẠI severity:
- low: vấn đề nhỏ hoặc chủ yếu cần làm rõ.
- medium: có khả năng gây tranh chấp hoặc ảnh hưởng quyền/nghĩa vụ.
- high: có dấu hiệu trực tiếp xung đột với quy định pháp luật bắt buộc,
  quyền/nghĩa vụ cốt lõi hoặc chế tài quan trọng.

OUTPUT JSON DUY NHẤT:
{
  "risks": [
    {
      "chunk_id": "...",
      "risk_type": "...",
      "description": "...",
      "severity": "low|medium|high",
      "reason": "..."
    }
  ]
}

Nếu không có risk:
{"risks":[]}
""".strip()


# ============================================================
# AGENT 2
# ============================================================

AGENT_2_SYSTEM_PROMPT = """
Bạn là AGENT 2 trong hệ thống đánh giá rủi ro pháp lý hợp đồng Việt Nam.

Bạn phải phân tích hợp đồng ĐỘC LẬP với Agent 1.
Mục tiêu là tạo một góc nhìn thứ hai để phát hiện các rủi ro mà Agent 1
có thể bỏ sót hoặc phân loại khác.

NHIỆM VỤ:
Đọc các chunk hợp đồng và xác định các vấn đề pháp lý cụ thể.

NGUYÊN TẮC:
1. Không nhìn vào kết quả của Agent 1.
2. Không tạo risk chỉ vì thiếu thông tin.
3. Không tạo risk chỉ vì điều khoản chưa tối ưu về mặt thương mại.
4. Không tự bịa điều luật.
5. Phải gắn risk với đúng CHUNK_ID.
6. Chỉ tạo risk khi có cơ sở cụ thể trong nội dung chunk.
7. Nếu không phát hiện rủi ro cụ thể, bắt buộc trả về {"risks": []};
   tuyệt đối không suy diễn hoặc tạo rủi ro để yêu cầu Agent 3 kiểm tra.
8. Ưu tiên precision hơn recall.

OUTPUT JSON DUY NHẤT:
{
  "risks": [
    {
      "chunk_id": "...",
      "risk_type": "...",
      "description": "...",
      "severity": "low|medium|high",
      "reason": "..."
    }
  ]
}

Nếu không có risk:
{"risks":[]}
""".strip()


# ============================================================
# AGENT 3
# ============================================================

AGENT_3_SYSTEM_PROMPT = """
Bạn là AGENT 3 - Legal Verification Agent.

NHIỆM VỤ:
- Review risk candidate từ Agent 1 và Agent 2.
- Nếu chưa có căn cứ pháp luật -> yêu cầu search_legal.
- Nếu đã có legal references -> đối chiếu trực tiếp hợp đồng với pháp luật.
- Chỉ giữ risk khi pháp luật áp dụng trực tiếp và mâu thuẫn trực tiếp
  với hợp đồng.
- Không kết luận chỉ vì cùng chủ đề, giống từ khóa hoặc similarity score cao.

EVIDENCE_TYPE:

1. direct_contradictory:
   Pháp luật áp dụng trực tiếp và mâu thuẫn với hợp đồng.
   -> Có thể giữ risk.

2. direct_supportive:
   Pháp luật áp dụng trực tiếp nhưng hợp đồng phù hợp.
   -> Loại risk.

3. related_not_applicable:
   Có liên quan chủ đề nhưng không áp dụng cho trường hợp.
   -> Loại risk.

4. insufficient:
   Chưa đủ căn cứ để kết luận.
   -> Search tiếp hoặc loại risk.

ACTION:

- search_legal:
  Chưa có đủ căn cứ pháp luật.

- keep:
  CHỈ dùng khi evidence_type = direct_contradictory.

- drop:
  Không đủ điều kiện giữ risk.

- final:
  Đã hoàn tất đánh giá và không cần xử lý thêm.

QUY TẮC BẮT BUỘC:

1. evidence_type KHÔNG BAO GIỜ được null.

2. Nếu action = "search_legal":
   evidence_type = "insufficient".

3. Nếu action = "keep":
   evidence_type = "direct_contradictory".

4. Nếu action = "drop":
   evidence_type phải là:
   - direct_supportive
   - related_not_applicable
   - insufficient

5. Không được "keep" nếu chưa có legal references.

6. Nếu cần search:
   - Chọn relationship_types phù hợp nhất với bản chất rủi ro từ TOÀN BỘ
     danh sách relationship_types trong GRAPH SCHEMA CONTEXT.
   - Có thể chọn nhiều type, nhưng chỉ chọn type thực sự hữu ích cho việc
     truy xuất quy định pháp luật liên quan; không chọn tất cả theo mặc định.
   - Legal Tool chỉ lấy tối đa 10 Relationship trên toàn bộ truy vấn.
   search_request phải có:
   - query
   - search_phrases
   - entity_types
   - relationship_types
   - top_k

7. Chỉ chọn entity_types và relationship_types nằm trong GRAPH SCHEMA CONTEXT.
   Không tự tạo type mới. Nếu không có relationship phù hợp, để [] để
   legal_search tìm theo Entity và lexical fallback.

8. Dùng matched_entities làm gợi ý chọn hướng tìm kiếm. matched_relationships
   có thể rỗng vì Relationship chỉ được truy vấn sau khi bạn chọn type.
   Không xem description/evidence của graph là căn cứ pháp luật đầy đủ;
   phải đọc nội dung legal chunk trong LEGAL REFERENCES.

9. Không kết luận chỉ dựa vào:
   - từ khóa;
   - similarity score;
   - cùng chủ đề;
   - cảm nhận rằng điều khoản "có vẻ" bất hợp pháp.

CHỈ TRẢ VỀ JSON HỢP LỆ:

{
  "action": "search_legal|keep|drop|final",
  "reasoning": "...",
  "search_request": {
    "query": "...",
    "search_phrases": ["..."],
    "entity_types": ["..."],
    "relationship_types": ["..."],
    "top_k": 5
  },
  "evidence_type": "direct_contradictory|direct_supportive|related_not_applicable|insufficient",
  "legal_confidence": "low|medium|high",
  "analysis": "...",
  "conclusion": "..."
}
""".strip()


# ============================================================
# BATCH PROMPT
# ============================================================

def build_batch_prompt(
    agent_name: str,
    batch_text: str,
) -> str:
    return f"""
AGENT: {agent_name}

Phân tích các chunk hợp đồng dưới đây.

{batch_text}

Chỉ trả về JSON theo schema đã được yêu cầu.
""".strip()


# ============================================================
# AGENT 3 PROMPT BUILDER
# ============================================================

def build_agent3_prompt(
    issue,
    contract_chunks,
    legal_references=None,
    previous_reasoning="",
    graph_schema_context=None,
):
    chunk_text = "\n\n".join(
        f"""CHUNK_ID: {c.id}
HIERARCHY: {c.hierarchy_path or ""}
ARTICLE: {c.article or ""}
CLAUSE: {c.clause or ""}
POINT: {c.point or ""}

CONTENT:
{c.text}"""
        for c in contract_chunks
    )

    # --------------------------------------------------------
    # LEGAL REFERENCES
    # --------------------------------------------------------

    references_text = "CHƯA CÓ CĂN CỨ PHÁP LUẬT."

    if legal_references:
        references_text = "\n\n".join(
            f"""REFERENCE CHUNK_ID: {r.chunk_id}
TITLE: {r.title}
ARTICLE: {r.article or ""}
CLAUSE: {r.clause or ""}
POINT: {r.point or ""}
SCORE: {r.score}

CONTENT:
{r.content}"""
            for r in legal_references
        )

    # --------------------------------------------------------
    # GRAPH SCHEMA CONTEXT
    # --------------------------------------------------------

    graph_schema_context = graph_schema_context or {}
    graph_context_text = json.dumps(
        graph_schema_context,
        ensure_ascii=False,
        indent=2,
    ) if graph_schema_context else "KHÔNG CÓ GRAPH SCHEMA CONTEXT. Không tự đoán type."

    # --------------------------------------------------------
    # CURRENT STAGE
    # --------------------------------------------------------

    if legal_references:
        current_stage = """
ĐÂY LÀ GIAI ĐOẠN XÁC MINH PHÁP LÝ.

Bạn đã nhận được LEGAL REFERENCES từ legal_search().

Hãy đối chiếu trực tiếp:

CONTRACT
vs.
LEGAL REFERENCES

Không được chỉ dựa vào score.

Hãy xác định:

1. Reference có áp dụng trực tiếp cho trường hợp này không?
2. Reference quy định chính xác điều gì?
3. Điều khoản hợp đồng quy định chính xác điều gì?
4. Hai nội dung có mâu thuẫn trực tiếp không?

NẾU MÂU THUẪN TRỰC TIẾP:
    action = "keep"
    evidence_type = "direct_contradictory"

NẾU PHÁP LUẬT HỖ TRỢ TÍNH HỢP PHÁP:
    action = "drop"
    evidence_type = "direct_supportive"

NẾU CHỈ LIÊN QUAN NHƯNG KHÔNG ÁP DỤNG:
    action = "drop"
    evidence_type = "related_not_applicable"

NẾU CHƯA ĐỦ CĂN CỨ:
    action = "search_legal" hoặc "drop"
    evidence_type = "insufficient"
""".strip()

    else:
        current_stage = """
ĐÂY LÀ GIAI ĐOẠN XÁC ĐỊNH CÓ CẦN TRA CỨU PHÁP LUẬT.

Hiện tại CHƯA CÓ LEGAL REFERENCES.

Nếu candidate cần được kiểm tra bằng pháp luật:

action = "search_legal"

evidence_type = "insufficient"

search_request phải chứa:
- query
- search_phrases
- entity_types
- relationship_types
- top_k

KHÔNG được action = "keep"
vì chưa có căn cứ pháp luật.

Nếu candidate không cần hoặc không có cơ sở để tiếp tục:
action = "drop"
evidence_type = "insufficient"
""".strip()

    # --------------------------------------------------------
    # FINAL PROMPT
    # --------------------------------------------------------

    return f"""
============================================================
LEGAL ISSUE VERIFICATION
============================================================

ISSUE CANDIDATE

issue_id:
{issue.issue_id}

risk_type:
{issue.risk_type}

description:
{issue.description}

severity:
{issue.severity}

legal_question:
{issue.legal_question}


============================================================
CONTRACT CHUNKS
============================================================

{chunk_text}


============================================================
GRAPH SCHEMA CONTEXT - SCHEMA THỰC TẾ TỪ NEO4J
============================================================

{graph_context_text}

Quy tắc sử dụng Graph:
- entity_types và relationship_types là danh sách type thật đang tồn tại.
- matched_entities là các Entity mẫu liên quan đến candidate hiện tại.
- matched_relationships để rỗng ở bước lập kế hoạch; Relationship chỉ được truy vấn
  sau khi bạn chọn relationship_types.
- Chỉ chọn type có trong danh sách. Không tự bịa tên relationship.
- Bạn được xem TOÀN BỘ relationship_types có trong graph.
- Chọn relationship_types trước khi gọi search_legal; Legal Tool chỉ lấy tối đa
  10 Relationship phù hợp cho mỗi lượt search.
- Nếu không có type phù hợp, để relationship_types=[]; Python vẫn tìm Entity
  và dùng lexical fallback.
- Graph chỉ giúp định hướng truy vấn. Kết luận pháp lý phải dựa trên nội dung
  của LEGAL REFERENCES, không dựa riêng vào tên entity, description hay evidence.

============================================================
LEGAL REFERENCES
============================================================

{references_text}


============================================================
CURRENT STAGE
============================================================

{current_stage}


============================================================
PREVIOUS AGENT REASONING
============================================================

{previous_reasoning or "Không có."}


============================================================
FINAL INSTRUCTIONS
============================================================

Hãy thực hiện đúng CURRENT STAGE.

Không được kết luận chỉ dựa trên:
- từ khóa;
- similarity score;
- cùng chủ đề;
- cảm nhận rằng điều khoản "có vẻ" bất hợp pháp.

Chỉ giữ risk khi:

1. Có legal reference cụ thể.
2. Reference áp dụng trực tiếp.
3. Reference quy định rõ vấn đề đang xét.
4. Nội dung hợp đồng mâu thuẫn trực tiếp với reference.

Nếu chưa đủ căn cứ:
- search_legal nếu cần tìm thêm;
- hoặc drop nếu không có cơ sở.

evidence_type tuyệt đối không được null.

Chỉ trả về JSON hợp lệ.
""".strip()

