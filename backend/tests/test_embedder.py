from embeddings.embedding_factory import EmbeddingFactory

embedder = EmbeddingFactory.create()
vector = embedder.embed_text(
    "Bên A có trách nhiệm thanh toán cho Bên B."
)

print("Dimension:", embedder.dimension)
print("Vector:", vector[:10])