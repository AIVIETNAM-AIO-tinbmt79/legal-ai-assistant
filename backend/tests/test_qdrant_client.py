from qdrant.qdrant_client import QdrantClientManager


manager = QdrantClientManager()

print("=" * 70)
print("QDRANT HEALTH CHECK")
print("=" * 70)

print(
    "Connected:",
    manager.health_check(),
)

print(
    "Client:",
    type(manager.get_client()).__name__,
)