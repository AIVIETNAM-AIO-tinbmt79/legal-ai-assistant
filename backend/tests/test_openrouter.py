from llm.llm_factory import LLMFactory


llm = LLMFactory.create(
    provider="openrouter"
)


response = llm.generate(
    "Hãy giải thích ngắn gọn RAG là gì."
)


print("=" * 70)
print("OPENROUTER TEST")
print("=" * 70)

print(response)