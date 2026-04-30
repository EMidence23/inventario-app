"""Acciones administrativas destructivas. Solo admin."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..auth import hash_password, require_admin
from ..db import get_db
from ..models import User

router = APIRouter(prefix="/api/admin", tags=["admin"])


# Orden importa: primero tablas hijas con FK, luego padres.
_WIPE_TABLES_IN_ORDER: tuple[str, ...] = (
    "audit_log",
    "caja_items",
    "caja_instaladores",
    "caja_plantilla_items",
    "cajas_herramienta",
    "caja_plantillas",
    "herramientas",
    "instaladores",
    "usage_records",
    "inventory_items",
)


@router.post("/factory-reset")
def factory_reset(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    confirm: str = Query(default=""),
) -> dict:
    """Borra TODOS los datos de negocio y deja un unico usuario admin.

    Requiere ?confirm=WIPE_ALL_DATA para evitar llamadas accidentales.
    Resetea el usuario que invoca a username=admin, password=admin123,
    role=admin, y elimina al resto de usuarios. Finalmente limpia la
    bitacora (audit_log) entera para que el sistema quede 'en blanco'.
    """
    if confirm != "WIPE_ALL_DATA":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Se requiere ?confirm=WIPE_ALL_DATA para ejecutar el factory reset",
        )

    counts: dict[str, int] = {}

    # 1) Datos de negocio
    for tbl in _WIPE_TABLES_IN_ORDER:
        try:
            pre = db.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar() or 0
            db.execute(text(f"DELETE FROM {tbl}"))
            counts[tbl] = int(pre)
        except Exception:
            # Si la tabla no existe en alguna version, seguimos. En
            # PostgreSQL un statement fallido deja la transaccion en
            # estado abortado, asi que hay que hacer rollback antes
            # de seguir; en SQLite el rollback es no-op.
            db.rollback()
            counts[tbl] = 0

    # 2) Usuarios: borrar todos menos el caller, y resetear al caller.
    other_users = db.query(User).filter(User.id != admin.id).count()
    db.query(User).filter(User.id != admin.id).delete(synchronize_session=False)

    admin_db = db.get(User, admin.id)
    if admin_db is not None:
        admin_db.username = "admin"
        admin_db.password_hash = hash_password("admin123")
        admin_db.role = "admin"

    counts["users_deleted"] = int(other_users)
    counts["admin_reset"] = 1

    # 3) Asegurar que la bitacora quede vacia despues del commit, por si
    # la escritura del propio delete genero alguna entrada adicional.
    db.commit()
    try:
        db.execute(text("DELETE FROM audit_log"))
        db.commit()
    except Exception:
        db.rollback()

    return {"status": "ok", "wiped": counts}
