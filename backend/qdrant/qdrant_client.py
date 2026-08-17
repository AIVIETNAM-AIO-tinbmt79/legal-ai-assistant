from qdrant_client import QdrantClient

from qdrant.qdrant_config import (
    QDRANT_URL,
    QDRANT_API_KEY,
)


class QdrantClientManager:
    """
    Manage connection to Qdrant.
    """

    def __init__(self):

        if QDRANT_API_KEY:
            self.client = QdrantClient(
                url=QDRANT_URL,
                api_key=QDRANT_API_KEY,
            )
        else:
            self.client = QdrantClient(
                url=QDRANT_URL,
            )

    def get_client(self) -> QdrantClient:
        """
        Return Qdrant client.
        """
        return self.client

    def health_check(self) -> bool:
        """
        Check whether Qdrant is reachable.
        """

        try:
            self.client.get_collections()
            return True

        except Exception:
            return False