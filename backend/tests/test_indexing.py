from pathlib import Path

from indexing.document_indexer import DocumentIndexer


# ==================================================
# CONFIG
# ==================================================

PATH_FILE = Path(
    r"D:\legal-ai-assistant\backend\data\sample_contracts\docx_test.docx"
)


# ==================================================
# Create Indexer
# ==================================================

print()
print("=" * 70)
print("DOCUMENT INDEXING")
print("=" * 70)

indexer = DocumentIndexer()


# ==================================================
# Index document
# ==================================================

result = indexer.index(
    PATH_FILE
)


# ==================================================
# Display result
# ==================================================

print()
print("=" * 70)
print("INDEXING RESULT")
print("=" * 70)

print("File:")
print(result["file"])

print()

print("Number of chunks:")
print(result["chunks"])

print()

print("Number of embeddings:")
print(result["embeddings"])

print()

print("Vector dimension:")
print(result["vector_dimension"])

print()

print("=" * 70)
print("INDEXING COMPLETED")
print("=" * 70)