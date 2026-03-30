from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class DTO(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class UserRegister(DTO):
    email: EmailStr
    password: str = Field(min_length=8)


class UserLogin(DTO):
    email: EmailStr
    password: str


class UserOut(DTO):
    id: UUID
    email: str
    is_active: bool
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ApiKeyCreate(DTO):
    label: str = "default"


class ApiKeyOut(DTO):
    id: UUID
    label: str
    key_prefix: str
    created_at: datetime
    last_used_at: Optional[datetime] = None


class ApiKeyCreatedOut(ApiKeyOut):
    raw_key: str
