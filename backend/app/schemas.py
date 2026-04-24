"""Pydantic schemas."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Role = Literal["admin", "empleado"]


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    role: Role


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1)
    role: Role = "empleado"


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=1, max_length=80)
    password: str | None = Field(default=None, min_length=1)
    role: Role | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=1)


class InventoryItemIn(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=200)
    cat: str = ""
    stock: int | None = Field(default=None, ge=0)
    cost: float | None = Field(default=None, ge=0)


class InventoryItemOut(BaseModel):
    id: int
    code: str
    name: str
    cat: str
    stock: int
    cost: float


class UsageItemIn(BaseModel):
    id: int
    code: str
    name: str
    qtyUsed: int = Field(ge=0)


class UsageRecordIn(BaseModel):
    items: list[UsageItemIn]
    # Fecha local del cliente (YYYY-MM-DD). Si no se envia se usa UTC.
    date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class UsageItemOut(BaseModel):
    id: int
    code: str
    name: str
    qtyUsed: int


class UsageRecordOut(BaseModel):
    id: int
    user: str
    date: str
    ts: str
    items: list[UsageItemOut]
