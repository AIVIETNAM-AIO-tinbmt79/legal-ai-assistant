from chunking.chunker_factory import ChunkerFactory


text = """
Bên A có trách nhiệm cung cấp dịch vụ theo đúng thời hạn đã thỏa thuận.

Bên B có trách nhiệm cung cấp đầy đủ thông tin và thanh toán đúng hạn.

Trong trường hợp một bên vi phạm nghĩa vụ, bên còn lại có quyền yêu cầu bồi thường thiệt hại.
"""


# ==============================
# Create chunker
# ==============================

chunker = ChunkerFactory.create(text)

print("=" * 70)
print("CHUNKER:", type(chunker).__name__)
print("=" * 70)


# ==============================
# Chunk document
# ==============================

chunks = chunker.chunk(text)


# ==============================
# Display chunks
# ==============================

for i, chunk in enumerate(chunks, start=1):

    print()
    print("=" * 70)
    print(f"CHUNK {i}")
    print("=" * 70)

    print("ID:", chunk.id)

    print("\nMETADATA:")
    print(chunk.metadata)

    print("\nTEXT:")
    print("-" * 70)
    print(chunk.text)
    print("-" * 70)