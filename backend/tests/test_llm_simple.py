from llm.llm_factory import LLMFactory


llm = LLMFactory.create()


prompt = """
Bạn là trợ lý phân tích hợp đồng.

Hãy trả lời câu hỏi bằng tiếng Việt.

NỘI DUNG HỢP ĐỒNG:

Điều 4: Giá trị hợp đồng, thời hạn và phương thức thanh toán.

4.1: Giá trị hợp đồng:
Tổng giá trị hợp đồng là: ....,...,000 VNĐ.

4.2: Thời hạn và phương thức thanh toán:
Được thanh toán thành 2 lần.

4.3: Phương thức thanh toán:
Bằng tiền mặt.

CÂU HỎI:

Điều 4 là gì?

CHỈ TRẢ VỀ CÂU TRẢ LỜI CUỐI CÙNG.
"""


print("=" * 70)
print("TEST LLM")
print("=" * 70)

answer = llm.generate(prompt)

print()
print("ANSWER:")
print(answer)