
import sqlite3
import uuid
from datetime import datetime, timezone
import jwt
import bcrypt
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPAuthorizationCredentials

from app.core.database import get_db, cleanup_expired_revoked_tokens
from app.schemas.auth import RegisterRequest, AuthResponse, UserResponse, LoginRequest
from app.core.security import create_access_token, get_current_user, bearer_scheme, get_secret_key, ALGORITHM
from app.schemas.auth import LoginResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED
)
def register(data: RegisterRequest):
    # 1. Kiểm tra mật khẩu xác nhận
    if data.password != data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu xác nhận không khớp."
        )

    # 2. Bcrypt chỉ xử lý tối đa 72 byte
    if len(data.password.encode("utf-8")) > 72:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu không được vượt quá 72 byte."
        )

    # 3. Chuẩn hóa dữ liệu
    username = data.username.strip()
    email = str(data.email).strip().lower()

    if not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username không được để trống."
        )

    # 4. Tạo password hash, không lưu mật khẩu gốc
    password_hash = bcrypt.hashpw(
        data.password.encode("utf-8"),
        bcrypt.gensalt(rounds=12)
    ).decode("utf-8")

    # 5. Lưu tài khoản vào database
    now = datetime.now(timezone.utc).isoformat()
    user_id = str(uuid.uuid4())

    connection = get_db()

    try:
        # Kiểm tra tài khoản đã tồn tại
        existing_user = connection.execute(
            """
            SELECT username, email
            FROM users
            WHERE username = ? COLLATE NOCASE
               OR email = ? COLLATE NOCASE
            LIMIT 1
            """,
            (username, email)
        ).fetchone()

        if existing_user:
            if existing_user["username"].lower() == username.lower():
                detail = "Username đã được sử dụng."
            else:
                detail = "Email đã được sử dụng."

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=detail
            )

        connection.execute(
            """
            INSERT INTO users (
                id,
                username,
                email,
                password_hash,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                username,
                email,
                password_hash,
                now,
                now
            )
        )

        connection.commit()

    except sqlite3.IntegrityError:
        connection.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username hoặc email đã được sử dụng."
        )

    finally:
        connection.close()

    return AuthResponse(
        message="Đăng ký tài khoản thành công.",
        user=UserResponse(
            id=user_id,
            username=username,
            email=email
        )
    )


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest):
    identifier = data.identifier.strip()
    connection =get_db()
    try:
        user = connection.execute(
            """
            SELECT id, username, email, password_hash
            FROM users
            WHERE username = ? COLLATE NOCASE
               OR email = ? COLLATE NOCASE
            LIMIT 1
            """,
            (identifier, identifier)
        ).fetchone()
    finally:
        connection.close()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Thông tin đăng nhập không chính xác."
        )

     # So sánh mật khẩu nhập vào với bcrypt hash trong database
    password_is_valid = bcrypt.checkpw(
        data.password.encode("utf-8"),
        user["password_hash"].encode("utf-8")
    )

    if not password_is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Thông tin đăng nhập không chính xác."
        )

    access_token = create_access_token(user["id"])

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user["id"],
            username=user["username"],
            email=user["email"]
        )
    )

@router.get("/me", response_model=UserResponse)
def read_current_user(
    user_id: str = Depends(get_current_user),
):
    connection = get_db()

    try:
        user = connection.execute(
            """
            SELECT id, username, email
            FROM users
            WHERE id = ?
            """,
            (user_id,)
        ).fetchone()
    finally:
        connection.close()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tài khoản không còn tồn tại.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserResponse(
        id=user["id"],
        username=user["username"],
        email=user["email"]
    )


@router.post("/logout")
def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
):
    # 1. Kiểm tra có gửi JWT hay không
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Vui lòng đăng nhập.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # 2. Xác minh JWT
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

    # 3. Lấy mã định danh và thời hạn của JWT
    jti = payload.get("jti")
    exp = payload.get("exp")

    if not jti or exp is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ.",
        )

    # 4. Dọn những token đã hết hạn
    cleanup_expired_revoked_tokens()

    # 5. Thu hồi JWT hiện tại
    connection = get_db()

    try:
        connection.execute(
            """
            INSERT OR IGNORE INTO revoked_tokens
                (jti, expires_at, revoked_at)
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