"""Pydantic models for authentication."""
from pydantic import BaseModel, EmailStr, field_validator


class RegisterRequest(BaseModel):
    """Request body for /auth/register."""
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    """Request body for /auth/login."""
    email: EmailStr
    password: str


class UserOut(BaseModel):
    """Public user representation returned by auth endpoints."""
    id: int
    email: str
