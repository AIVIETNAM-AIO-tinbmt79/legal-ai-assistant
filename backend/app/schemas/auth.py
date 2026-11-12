from pydantic import BaseModel, EmailStr, Field, ConfigDict

class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=20)
    password: str = Field(min_length=8, max_length=72)
    confirm_password: str = Field(min_length=8, max_length=72)

    model_config = ConfigDict(str_strip_whitespace=True)

class LoginRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=72)

class UserResponse(BaseModel):
    id: str
    username: str
    email: str

class AuthResponse(BaseModel):
    message: str
    user: UserResponse

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse