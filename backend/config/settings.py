import os
from pathlib import Path

from dotenv import load_dotenv


# ==================================================
# BASE PATH
# ==================================================


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


class Settings:

    # ==================================================
    # PATHS
    # ==================================================

    BASE_DIR = PROJECT_ROOT

    DATA_DIR = (
        BASE_DIR / "data"
    )

    DATA_DIR.mkdir(
        exist_ok=True
    )

    DATABASE_PATH = (
        DATA_DIR / "legal_ai.db"
    )

    DATABASE_URL = (
        f"sqlite:///{DATABASE_PATH}"
    )


    # ==================================================
    # EMBEDDING
    # ==================================================

    EMBEDDING_MODEL = os.getenv(
        "EMBEDDING_MODEL",
        "intfloat/multilingual-e5-small",
    )

    EMBEDDING_DEVICE = os.getenv(
        "EMBEDDING_DEVICE",
        "cpu",
    )


    # ==================================================
    # VECTOR DATABASE
    # ==================================================

    QDRANT_URL = os.getenv(
        "QDRANT_URL",
        "http://localhost:6333",
    )

    QDRANT_COLLECTION = os.getenv(
        "QDRANT_COLLECTION",
        "legal_documents",
    )

    QDRANT_API_KEY = os.getenv(
        "QDRANT_API_KEY",
    )


    # ==================================================
    # RETRIEVAL
    # ==================================================

    RETRIEVAL_TOP_K = int(
        os.getenv(
            "RETRIEVAL_TOP_K",
            20,
        )
    )

    SEMANTIC_WEIGHT = float(
        os.getenv(
            "SEMANTIC_WEIGHT",
            0.7,
        )
    )

    BM25_WEIGHT = float(
        os.getenv(
            "BM25_WEIGHT",
            0.3,
        )
    )

    BACKEND_ROOT = Path(__file__).resolve().parents[1]

    _bm25_index_path = Path(
        os.getenv(
            "BM25_INDEX_PATH",
            str(BACKEND_ROOT / "storage" / "bm25" / "bm25_index.pkl"),
        )
    )

    BM25_INDEX_PATH = (
        _bm25_index_path
        if _bm25_index_path.is_absolute()
        else BACKEND_ROOT / _bm25_index_path
    )


    # ==================================================
    # Reranker
    # ==================================================

    RERANKER_MODEL = os.getenv(
        "RERANKER_MODEL",
        "BAAI/bge-reranker-v2-m3",
    )

    RERANKER_DEVICE = os.getenv(
        "RERANKER_DEVICE",
        "cpu",
    )

    RERANKER_MAX_LENGTH = int(
        os.getenv(
            "RERANKER_MAX_LENGTH",
            "1024",
        )
    )

    RERANKER_SEGMENT_TOKENS = int(
        os.getenv(
            "RERANKER_SEGMENT_TOKENS",
            "450",
        )
    )

    RERANKER_SEGMENT_OVERLAP = int(
        os.getenv(
            "RERANKER_SEGMENT_OVERLAP",
            "50",
        )
    )

    RERANKER_TOP_K = int(
        os.getenv(
            "RERANKER_TOP_K",
            "5",
        )
    )

    # ==================================================
    # MEMORY
    # ==================================================

    MEMORY_MAX_MESSAGES = int(
        os.getenv(
            "MEMORY_MAX_MESSAGES",
            10,
        )
    )

    # ==================================================
    # JWT AUTHENTICATION
    # ==================================================

    JWT_SECRET_KEY = os.getenv(
        "JWT_SECRET_KEY"
    )

    JWT_ALGORITHM = os.getenv(
        "JWT_ALGORITHM",
        "HS256",
    )

    JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(
        os.getenv(
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
            60,
        )
    )

    # ==================================================
    # CHUNKING
    # ==================================================

    CHUNK_MAX_CHARS = int(
        os.getenv(
            "CHUNK_MAX_CHARS",
            4000,
        )
    )

    CHUNK_OVERLAP = int(
        os.getenv(
            "CHUNK_OVERLAP",
            200,
        )
    )


    # ==================================================
    # OPENROUTER / LLM
    # ==================================================

    OPENROUTER_API_KEY = os.getenv(
        "OPENROUTER_API_KEY"
    )

    OPENROUTER_BASE_URL = os.getenv(
        "OPENROUTER_BASE_URL",
        "https://openrouter.ai/api/v1",
    )

    OPENROUTER_MODEL = os.getenv(
        "OPENROUTER_MODEL",
        "openrouter/free",
    )

    OPENROUTER_TEMPERATURE = float(
        os.getenv(
            "OPENROUTER_TEMPERATURE",
            0,
        )
    )

    OPENROUTER_MAX_TOKENS = int(
        os.getenv(
            "OPENROUTER_MAX_TOKENS",
            1000,
        )
    )

    # ==================================================
    # FASTAPI
    # ==================================================

    APP_NAME = os.getenv(
        "APP_NAME",
        "Legal AI Assistant API",
    )

    APP_VERSION = os.getenv(
        "APP_VERSION",
        "1.0.0",
    )

    API_HOST = os.getenv(
        "API_HOST",
        "0.0.0.0",
    )

    API_PORT = int(
        os.getenv(
            "API_PORT",
            "8000",
        )
    )

    CORS_ORIGINS = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:8501,http://127.0.0.1:8501",
        ).split(",")
        if origin.strip()
    ]


    # ==================================================
    # VALIDATION
    # ==================================================

    def validate(self):

        required_settings = {

            "OPENROUTER_API_KEY":
                self.OPENROUTER_API_KEY,

            "JWT_SECRET_KEY":
                self.JWT_SECRET_KEY,
        }

        missing = [

            name

            for name, value
            in required_settings.items()

            if not value
        ]

        if missing:

            raise ValueError(
                "Missing environment variables: "
                + ", ".join(
                    missing
                )
            )

        # ----------------------------------------------

        if (
            self.SEMANTIC_WEIGHT
            + self.BM25_WEIGHT
            != 1.0
        ):

            raise ValueError(
                "SEMANTIC_WEIGHT + BM25_WEIGHT "
                "must equal 1.0"
            )

        # ----------------------------------------------

        if (
            self.CHUNK_OVERLAP
            >= self.CHUNK_MAX_CHARS
        ):

            raise ValueError(
                "CHUNK_OVERLAP must be smaller "
                "than CHUNK_MAX_CHARS"
            )

        # ----------------------------------------------

        if self.MEMORY_MAX_MESSAGES <= 0:

            raise ValueError(
                "MEMORY_MAX_MESSAGES "
                "must be greater than 0"
            )

        


# ==================================================
# GLOBAL SETTINGS
# ==================================================

settings = Settings()