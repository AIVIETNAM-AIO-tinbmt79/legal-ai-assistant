
import os
from pathlib import Path

from dotenv import load_dotenv

# Thư mục gốc của dự án
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Đọc file .env ở thư mục gốc
load_dotenv(PROJECT_ROOT / ".env")

# URL của backend API
API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "http://127.0.0.1:8000"
).rstrip("/")
