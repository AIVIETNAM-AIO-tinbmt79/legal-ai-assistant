class PromptBuilder:
    """
    Build prompts for the RAG pipeline.
    """

    SYSTEM_PROMPT = """
# Nhiệm vụ
    Bạn là trợ lý AI phân tích hợp đồng.

    Hãy trả lời câu hỏi của người dùng dựa trên
    thông tin được cung cấp trong CONTEXT.

# Quy tắc:
    1. Chỉ sử dụng thông tin có trong CONTEXT.
    2. Không tự bịa thông tin không có trong tài liệu.
    3. Nếu CONTEXT không đủ thông tin, hãy nói rõ rằng
    tài liệu không cung cấp đủ thông tin để kết luận.
    4. Khi có thể, hãy chỉ ra điều/khoản liên quan.
    5. Trả lời bằng tiếng Việt, rõ ràng và chính xác.
""".strip()

    def build(
        self,
        query: str,
        context: str,
    ) -> str:

        return f"""
{self.SYSTEM_PROMPT}

CONTEXT:

{context}

QUESTION

{query}

ANSWER
""".strip()