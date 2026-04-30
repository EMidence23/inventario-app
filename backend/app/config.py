"""Configuracion de la aplicacion."""
from __future__ import annotations

import os
import secrets
from pathlib import Path


def _resolve_database_url() -> str:
    """Usa /data (volumen persistente) si existe, si no SQLite local."""
    explicit = os.getenv("DATABASE_URL")
    if explicit:
        return explicit
    data_dir = Path("/data")
    if data_dir.is_dir() and os.access(data_dir, os.W_OK):
        return f"sqlite:///{data_dir / 'inventario.db'}"
    return "sqlite:///./inventario.db"


def _resolve_cors_origins() -> list[str]:
    """Lee CORS_ORIGINS como lista separada por comas. Default: permite todo."""
    raw = os.getenv("CORS_ORIGINS")
    if not raw:
        return ["*"]
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    return origins or ["*"]


def _resolve_jwt_secret() -> str:
    explicit = os.getenv("JWT_SECRET")
    if explicit:
        return explicit
    data_dir = Path("/data")
    if data_dir.is_dir() and os.access(data_dir, os.W_OK):
        secret_file = data_dir / "jwt_secret"
        if secret_file.exists():
            return secret_file.read_text().strip()
        new_secret = secrets.token_urlsafe(64)
        secret_file.write_text(new_secret)
        return new_secret
    # Fallback ephemeral (en dev). Reinicio invalida tokens, aceptable.
    return secrets.token_urlsafe(64)


class Settings:
    database_url: str = _resolve_database_url()
    jwt_secret: str = _resolve_jwt_secret()
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24 * 30  # 30 dias
    cors_origins: list[str] = _resolve_cors_origins()


settings = Settings()
