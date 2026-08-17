import os

from dotenv import load_dotenv


load_dotenv()


QDRANT_URL = os.getenv(
    "QDRANT_URL",
    "http://localhost:6333",
)

QDRANT_API_KEY = os.getenv(
    "QDRANT_API_KEY",
)

QDRANT_COLLECTION = os.getenv(
    "QDRANT_COLLECTION",
    "legal_documents",
)