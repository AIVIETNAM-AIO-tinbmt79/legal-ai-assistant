from qdrant_client import QdrantClient

from config.settings import settings


class QdrantClientManager:
    """
    Manage connection to Qdrant.
    """

    def __init__(self):

        self.url = settings.QDRANT_URL
        self.api_key = settings.QDRANT_API_KEY

        # ==========================================
        # Initialize Qdrant Client
        # ==========================================

        if self.api_key:

            self.client = QdrantClient(
                url=self.url,
                api_key=self.api_key,
            )

        else:

            self.client = QdrantClient(
                url=self.url,
            )


    # ==================================================
    # Get Client
    # ==================================================

    def get_client(self) -> QdrantClient:
        """
        Return Qdrant client.
        """

        return self.client


    # ==================================================
    # Health Check
    # ==================================================

    def health_check(self) -> bool:
        """
        Check whether Qdrant is reachable.
        """

        try:

            self.client.get_collections()

            return True

        except Exception:

            return False