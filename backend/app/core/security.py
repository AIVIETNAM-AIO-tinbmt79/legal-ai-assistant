
from datetime import datetime, timedelta, timezone
import uuid
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from config import settings
from app.core.database import get_db

st = settings.Settings
ALGORITHM = st.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = st.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
SECRET_KEY = st.JWT_SECRET_KEY
bearer_scheme = HTTPBearer(auto_error=False)

def get_secret_key():
    secret_key = SECRET_KEY
    if not secret_key:
        raise RuntimeError(
            "Chưa cấu hình biến môi trường JWT_SECRET_KEY."
        )

    return secret_key

def create_access_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "sub": user_id,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        ),
}

    return jwt.encode(
        payload,
        get_secret_key(),
        algorithm=ALGORITHM,
    )

def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
):
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Vui lòng đăng nhập.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            get_secret_key(),
            algorithms=[ALGORITHM],
        )

        jti = payload.get("jti")

        if not jti or is_token_revoked(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token không hợp lệ hoặc đã bị thu hồi.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token không hợp lệ.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user_id

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ hoặc đã hết hạn.",
            headers={"WWW-Authenticate": "Bearer"},
        )

def is_token_revoked(jti: str) -> bool:
    connection = get_db()

    try:
        row = connection.execute(
            "SELECT 1 FROM revoked_tokens WHERE jti = ?",
            (jti,),
        ).fetchone()

        return row is not None
    finally:
        connection.close()