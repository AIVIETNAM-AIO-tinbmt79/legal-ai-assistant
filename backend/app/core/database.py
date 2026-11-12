
import sqlite3
from pathlib import Path
from datetime import datetime, timezone


# Xác định thư mục gốc của dự án
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Sử dụng database hiện có, không tạo database mới
DATABASE_PATH = PROJECT_ROOT / "data" / "legal_ai.db"


def get_db():
    connection = sqlite3.connect(
        DATABASE_PATH,
        timeout=10
    )

    # Cho phép truy cập dữ liệu bằng tên cột
    connection.row_factory = sqlite3.Row

    # Bật kiểm tra khóa ngoại
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def init_revoked_tokens_table():
    connection = get_db()

    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS revoked_tokens (
                jti TEXT PRIMARY KEY,
                expires_at INTEGER NOT NULL,
                revoked_at TEXT NOT NULL
            )
            """
        )
        connection.commit()
    finally:
        connection.close()


def cleanup_expired_revoked_tokens():
    connection = get_db()

    try:
        now = int(datetime.now(timezone.utc).timestamp())

        connection.execute(
            """
            DELETE FROM revoked_tokens
            WHERE expires_at <= ?
            """,
            (now,),
        )

        connection.commit()
    finally:
        connection.close()