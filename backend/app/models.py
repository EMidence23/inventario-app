"""ORM models."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="empleado")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    cat: Mapped[str] = mapped_column(String(80), default="")
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class UsageRecord(Base):
    __tablename__ = "usage_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    username_snapshot: Mapped[str] = mapped_column(String(80), default="")
    date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    items_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")


class Instalador(Base):
    __tablename__ = "instaladores"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Herramienta(Base):
    __tablename__ = "herramientas"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CajaHerramienta(Base):
    """Una entrega de caja de herramientas a un grupo de instaladores en un
    dia especifico. Creada por admin o empleado; revisada por admin o
    empleado al final del dia para verificar el regreso."""

    __tablename__ = "cajas_herramienta"

    id: Mapped[int] = mapped_column(primary_key=True)
    fecha: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    hora_entrega: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    creada_por_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    creada_por_username: Mapped[str] = mapped_column(String(80), default="")
    revisada_por_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    revisada_por_username: Mapped[str] = mapped_column(String(80), default="")
    hora_revision: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notas: Mapped[str] = mapped_column(Text, default="")

    instaladores: Mapped[list["CajaInstalador"]] = relationship(
        "CajaInstalador", back_populates="caja", cascade="all, delete-orphan"
    )
    items: Mapped[list["CajaItem"]] = relationship(
        "CajaItem", back_populates="caja", cascade="all, delete-orphan"
    )


class CajaInstalador(Base):
    """Relacion M2M: una caja puede ir a uno o varios instaladores."""

    __tablename__ = "caja_instaladores"
    __table_args__ = (UniqueConstraint("caja_id", "instalador_id", name="uq_caja_instalador"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    caja_id: Mapped[int] = mapped_column(ForeignKey("cajas_herramienta.id", ondelete="CASCADE"), nullable=False, index=True)
    instalador_id: Mapped[int] = mapped_column(ForeignKey("instaladores.id", ondelete="CASCADE"), nullable=False, index=True)
    instalador_nombre_snapshot: Mapped[str] = mapped_column(String(120), default="")

    caja: Mapped["CajaHerramienta"] = relationship("CajaHerramienta", back_populates="instaladores")


class CajaItem(Base):
    """Herramienta entregada dentro de una caja.

    cantidad_entregada = cuantas salieron en la caja.
    cantidad_devuelta  = cuantas regresaron al revisar.
    estado = 'pendiente' (sin revisar), 'devuelta' (completo) o 'faltante'.
    """

    __tablename__ = "caja_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    caja_id: Mapped[int] = mapped_column(ForeignKey("cajas_herramienta.id", ondelete="CASCADE"), nullable=False, index=True)
    herramienta_id: Mapped[int] = mapped_column(ForeignKey("herramientas.id", ondelete="RESTRICT"), nullable=False)
    herramienta_nombre_snapshot: Mapped[str] = mapped_column(String(120), default="")
    cantidad_entregada: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cantidad_devuelta: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estado: Mapped[str] = mapped_column(String(16), nullable=False, default="pendiente")

    caja: Mapped["CajaHerramienta"] = relationship("CajaHerramienta", back_populates="items")
