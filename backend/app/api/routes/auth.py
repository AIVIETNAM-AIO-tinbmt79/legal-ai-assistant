from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_current_user
from app.api.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    UserResponse,
)

from auth.jwt import create_access_token
from auth.password import (
    hash_password,
    verify_password,
)

from app.database.models.user import UserModel
from app.database.repositories.user_repository import UserRepository


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


# ==================================================
# REGISTER
# ==================================================

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db),
):

    user_repository = UserRepository(db)


    # ----------------------------------------------
    # CHECK USERNAME
    # ----------------------------------------------

    if user_repository.exists_by_username(
        data.username
    ):

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )


    # ----------------------------------------------
    # CHECK EMAIL
    # ----------------------------------------------

    if user_repository.exists_by_email(
        data.email
    ):

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists",
        )


    # ----------------------------------------------
    # HASH PASSWORD
    # ----------------------------------------------

    password_hash = hash_password(
        data.password
    )


    # ----------------------------------------------
    # CREATE USER
    # ----------------------------------------------

    user = user_repository.create(
        username=data.username,
        email=data.email,
        password_hash=password_hash,
    )

    return user


# ==================================================
# LOGIN
# ==================================================

@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    data: LoginRequest,
    db: Session = Depends(get_db),
):

    user_repository = UserRepository(db)


    # ----------------------------------------------
    # FIND USER
    # ----------------------------------------------

    user = user_repository.get_by_email(
        data.email
    )


    # ----------------------------------------------
    # CHECK USER + PASSWORD
    # ----------------------------------------------

    if (
        user is None
        or not verify_password(
            data.password,
            user.password_hash,
        )
    ):

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )


    # ----------------------------------------------
    # CREATE JWT
    # ----------------------------------------------

    access_token = create_access_token(
        user_id=user.id
    )


    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
    )


# ==================================================
# CURRENT USER
# ==================================================

@router.get(
    "/me",
    response_model=UserResponse,
)
def get_me(
    current_user: UserModel = Depends(
        get_current_user
    ),
):

    return current_user