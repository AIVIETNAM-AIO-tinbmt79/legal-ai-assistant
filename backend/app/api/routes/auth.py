
import sqlite3
import uuid
from datetime import datetime, timezone

import bcrypt
import jwt

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import (
    get_db as get_sqlite_db,
    cleanup_expired_revoked_tokens,
)
from app.core.security import (
    create_access_token,
    get_current_user,
    bearer_scheme,
    get_secret_key,
    ALGORITHM,
)
from app.database.database import get_db as get_database_session
from app.database.repositories.user_repository import UserRepository
from app.schemas.auth import (
    RegisterRequest,
    AuthResponse,
    UserResponse,
    LoginRequest,
    LoginResponse,
)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    data: RegisterRequest,
    db: Session = Depends(get_database_session),
):
    # 1. Kiểm tra mật khẩu xác nhận.
    if data.password != data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu xác nhận không khớp.",
        )

    # 2. Bcrypt chỉ xử lý tối đa 72 byte.
    if len(data.password.encode("utf-8")) > 72:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu không được vượt quá 72 byte.",
        )

    # 3. Chuẩn hóa dữ liệu.
    username = data.username.strip()
    email = str(data.email).strip().lower()

    if not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username không được để trống.",
        )

    # 4. Khởi tạo repository với SQLAlchemy Session.
    user_repository = UserRepository(db)

    # 5. Kiểm tra username đã tồn tại.
    if user_repository.get_by_username(username) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username đã được sử dụng.",
        )

    # 6. Kiểm tra email đã tồn tại.
    if user_repository.get_by_email(email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email đã được sử dụng.",
        )

    # 7. Hash mật khẩu, không lưu mật khẩu gốc.
    password_hash = bcrypt.hashpw(
        data.password.encode("utf-8"),
        bcrypt.gensalt(rounds=12),
    ).decode("utf-8")

    # 8. Tạo thông tin tài khoản.
    now = datetime.now(timezone.utc)
    user_id = str(uuid.uuid4())

    # 9. Lưu tài khoản.
    try:
        user = user_repository.create(
            user_id=user_id,
            username=username,
            email=email,
            password_hash=password_hash,
            created_at=now,
            updated_at=now,
        )

    except IntegrityError:
        # Phòng trường hợp nhiều yêu cầu đăng ký đồng thời.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username hoặc email đã được sử dụng.",
        )

    return AuthResponse(
        message="Đăng ký tài khoản thành công.",
        user=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
        ),
    )


@router.post(
    "/login",
    response_model=LoginResponse,
)
def login(
    data: LoginRequest,
    db: Session = Depends(get_database_session),
):
    # 1. Tìm người dùng bằng username hoặc email.
    identifier = data.identifier.strip()
    user_repository = UserRepository(db)
    user = user_repository.get_by_identifier(identifier)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Thông tin đăng nhập không chính xác.",
        )

    # 2. Kiểm tra giới hạn byte của bcrypt.
    password_bytes = data.password.encode("utf-8")

    if len(password_bytes) > 72:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Thông tin đăng nhập không chính xác.",
        )

    # 3. So sánh mật khẩu với hash trong database.
    password_is_valid = bcrypt.checkpw(
        password_bytes,
        user.password_hash.encode("utf-8"),
    )

    if not password_is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Thông tin đăng nhập không chính xác.",
        )

    # 4. Tạo JWT.
    access_token = create_access_token(user.id)

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
        ),
    )


@router.get(
    "/me",
    response_model=UserResponse,
)
def read_current_user(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_database_session),
):
    # Lấy thông tin tài khoản từ SQLAlchemy repository.
    user = UserRepository(db).get_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tài khoản không còn tồn tại.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
    )


@router.post("/logout")
def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
):
    # 1. Kiểm tra có gửi JWT hay không.
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Vui lòng đăng nhập.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # 2. Xác minh JWT.
    try:
        payload = jwt.decode(
            token,
            get_secret_key(),
            algorithms=[ALGORITHM],
        )

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ hoặc đã hết hạn.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Lấy mã định danh và thời hạn của JWT.
    jti = payload.get("jti")
    exp = payload.get("exp")

    if not jti or exp is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 4. Dọn các token đã hết hạn.
    cleanup_expired_revoked_tokens()

    # 5. Thu hồi JWT hiện tại bằng SQLite.
    connection = get_sqlite_db()

    try:
        connection.execute(
            """
            INSERT OR IGNORE INTO revoked_tokens (
                jti,
                expires_at,
                revoked_at
            )
            VALUES (?, ?, ?)
            """,
            (
                jti,
                int(exp),
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        connection.commit()

    finally:
        connection.close()

    return {
        "message": "Đăng xuất thành công."
    }
    