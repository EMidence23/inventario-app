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


class InventoryBulkRow(BaseModel):
    """Fila de un Excel/CSV para actualizacion masiva.
    Solo 'code' es obligatorio. Los otros campos son opcionales y, si no
    vienen, NO se tocan en el producto existente."""

    code: str = Field(min_length=1, max_length=40)
    stock: int | None = Field(default=None, ge=0)
    # Costo que viene en el archivo, CON ISV incluido (como el Excel real
    # del usuario). El backend lo divide entre (1 + isv_rate) para guardar
    # el costo sin ISV.
    cost_with_isv: float | None = Field(default=None, ge=0)
    name: str | None = Field(default=None, max_length=200)
    cat: str | None = Field(default=None, max_length=80)


class InventoryBulkIn(BaseModel):
    rows: list[InventoryBulkRow] = Field(min_length=1)
    isv_rate: float = Field(default=0.15, ge=0, le=1)
    commit: bool = False


class InventoryBulkResultRow(BaseModel):
    code: str
    name: str | None = None
    action: Literal["updated", "skipped_not_found", "skipped_no_changes", "invalid"]
    changes: list[str]
    reason: str | None = None


class InventoryBulkOut(BaseModel):
    total_rows: int
    would_update: int
    not_found: int
    no_changes: int
    invalid: int
    committed: bool
    results: list[InventoryBulkResultRow]


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


# ── Instaladores / Herramientas / Cajas ──────────────────────────────
class InstaladorIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    activo: bool = True


class InstaladorOut(BaseModel):
    id: int
    nombre: str
    activo: bool


class HerramientaIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    activo: bool = True


class HerramientaOut(BaseModel):
    id: int
    nombre: str
    activo: bool


class CajaItemIn(BaseModel):
    herramienta_id: int
    cantidad_entregada: int = Field(ge=0)


class CajaItemOut(BaseModel):
    id: int
    herramienta_id: int
    herramienta_nombre: str
    cantidad_entregada: int
    cantidad_devuelta: int
    estado: str


class CajaHerramientaIn(BaseModel):
    fecha: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    instalador_ids: list[int] = Field(min_length=1)
    items: list[CajaItemIn] = Field(min_length=1)
    notas: str = ""


class CajaItemReview(BaseModel):
    id: int
    cantidad_devuelta: int = Field(ge=0)


class CajaRevisionIn(BaseModel):
    items: list[CajaItemReview]
    notas: str | None = None


class PlantillaItemIn(BaseModel):
    herramienta_id: int
    cantidad: int = Field(ge=1)


class PlantillaItemOut(BaseModel):
    herramienta_id: int
    herramienta_nombre: str
    cantidad: int


class PlantillaIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    items: list[PlantillaItemIn] = Field(min_length=1)


class PlantillaOut(BaseModel):
    id: int
    nombre: str
    items: list[PlantillaItemOut]


class CajaHerramientaOut(BaseModel):
    id: int
    fecha: str
    hora_entrega: str
    creada_por: str
    revisada_por: str | None
    hora_revision: str | None
    instaladores: list[str]
    items: list[CajaItemOut]
    total_entregadas: int
    total_devueltas: int
    total_faltantes: int
    estado: str
    notas: str
