import os

from dotenv import load_dotenv

from backend.config.settings import Settings
load_dotenv()

settings = Settings
QDRANT_URL = settings.QDRANT_URL

QDRANT_API_KEY = settings.QDRANT_API_KEY

QDRANT_COLLECTION = settings.QDRANT_COLLECTION