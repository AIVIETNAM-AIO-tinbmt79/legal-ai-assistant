from llm.llm_factory import LLMFactory


# ==================================================
# Create LLM
# ==================================================

llm = LLMFactory.create()

print("=" * 70)
print("LLM TEST")
print("=" * 70)

print()
print("LLM:", type(llm).__name__)

print()
print("Model:", llm.model)


# ==================================================
# Test
# ==================================================

prompt = """
Bạn là trợ lý AI.

Hãy trả lời câu hỏi sau bằng tiếng Việt.

Câu hỏi:
Việt Nam nằm ở châu nào?

Chỉ cần trả lời một câu ngắn gọn.
""".strip()


print()
print("Sending request...")


try:

    response = llm.generate(
        prompt
    )

    print()
    print("=" * 70)
    print("RAW RESPONSE")
    print("=" * 70)

    print("Type:")
    print(type(response))

    print()
    print("repr:")
    print(repr(response))

    print()
    print("Response:")
    print(response)

except Exception as e:

    print()
    print("=" * 70)
    print("LLM ERROR")
    print("=" * 70)

    print(
        type(e).__name__,
        ":",
        e,
    )