"""
認證相關的 Pydantic Schema
"""
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """登入請求"""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """登入成功回應"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """換發 Token 請求"""
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    """修改密碼請求"""
    old_password: str
    new_password: str
