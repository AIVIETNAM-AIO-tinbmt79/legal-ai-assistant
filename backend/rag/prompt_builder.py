class PromptBuilder:
    """
    Build the final prompt for the LLM.
    """

    def build(
        self,
        query: str,
        context: str,
        memory: str = "",
    ) -> str:

        prompt = """
Bạn là trợ lý AI chuyên phân tích hợp đồng.

Nhiệm vụ:
Trả lời câu hỏi của người dùng CHỈ dựa trên nội dung hợp đồng được cung cấp.

QUY TẮC:
1. Chỉ sử dụng thông tin có trong CONTEXT.
2. Không tự suy đoán hoặc bổ sung thông tin không có trong CONTEXT.
3. Nếu CONTEXT không đủ thông tin, hãy nói rõ rằng hợp đồng không cung cấp đủ thông tin.
4. Nếu có thể, nêu điều khoản liên quan, ví dụ: "Theo Điều 3.2..."
5. Trả lời bằng tiếng Việt.
6. Trả lời trực tiếp, ngắn gọn và dễ đọc.
7. Không được viết quá trình suy nghĩ, phân tích, reasoning hoặc thinking process.
8. Chỉ trả về câu trả lời cuối cùng cho người dùng.
9. Không được mô tả cách bạn tìm kiếm hoặc xử lý CONTEXT.
10. Không sử dụng bảng Markdown nếu không cần thiết.
"""

        # ==================================================
        # Conversation Memory
        # ==================================================

        if memory and memory.strip():

            prompt += """

LỊCH SỬ HỘI THOẠI:

"""

            prompt += memory.strip()

            prompt += """

"""

        # ==================================================
        # Retrieved Context
        # ==================================================

        prompt += """

CONTEXT:

"""

        if context and context.strip():

            prompt += context.strip()

        else:

            prompt += (
                "Không tìm thấy nội dung liên quan "
                "trong hợp đồng."
            )

        # ==================================================
        # Current Question
        # ==================================================

        prompt += """

CÂU HỎI:

"""

        prompt += query.strip()

        prompt += """

TRẢ LỜI:

"""

        return prompt.strip()