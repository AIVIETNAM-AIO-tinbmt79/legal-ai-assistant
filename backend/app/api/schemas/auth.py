from pydantic import BaseModel, EmailStr, Field


# ==================================================
# REGISTER
# ==================================================

class RegisterRequest(BaseModel):

    username: str = Field(
        min_length=3,
        max_length=100,
    )

    email: EmailStr

    password: str = Field(
        min_length=6,
        max_length=128,
    )


# ==================================================
# LOGIN
# ==================================================

class LoginRequest(BaseModel):

    email: EmailStr

    password: str = Field(
        min_length=6,
        max_length=128,
    )


# ==================================================
# TOKEN
# ==================================================

class TokenResponse(BaseModel):

    access_token: str

    token_type: str = "bearer"


# ==================================================
# USER
# ==================================================

class UserResponse(BaseModel):

    id: str

    username: str

    email: EmailStr

    model_config = {
        "from_attributes": True,
    }