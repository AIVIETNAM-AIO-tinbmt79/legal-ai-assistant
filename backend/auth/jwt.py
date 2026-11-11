from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from config.settings import settings


def create_access_token(
    user_id: str,
) -> str:

    expire = (
        datetime.now(timezone.utc)
        + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )

    payload = {
        "sub": user_id,
        "exp": expire,
    }

    token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    return token


def decode_access_token(
    token: str,
) -> str | None:

    try:

        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[
                settings.JWT_ALGORITHM
            ],
        )

        user_id = payload.get("sub")

        if not user_id:
            return None

        return user_id

    except JWTError:

        return None