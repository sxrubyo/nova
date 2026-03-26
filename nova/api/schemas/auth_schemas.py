"""Authentication request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel


class RegisterRequest(BaseModel):
    workspace_name: str
    owner_name: str
    email: str
    password: str
    plan: str = "free"


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    workspace_id: str
    workspace_name: str
    api_key: str | None = None


class MeResponse(BaseModel):
    workspace_id: str
    email: str
    role: str
