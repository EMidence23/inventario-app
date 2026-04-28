"""Lectura de la bitacora de actividad. Solo admin.

Soporta filtros opcionales:
- rango: hoy | semana | mes | all (default 'hoy', el caso comun de uso).
- usuario: filtra por username_snapshot exacto.
- accion: filtra por action exacto (ej: 'inventory_delete').
- categoria: agrupador grueso ('inventario', 'usos', 'cajas', 'usuarios',
  'login') que mapea a un set de actions.
- limit: tope de filas, por defecto 500. Maximo 5000.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..auth import require_admin
from ..db import get_db
from ..models import AuditLog, User
from ..schemas import AuditLogOut


router = APIRouter(prefix="/api/audit-log", tags=["audit"])


# Categorias agrupan acciones relacionadas para el filtro del frontend.
# Si no agrega ruido, listamos cada accion explicita aqui asi cuando
# agreguemos mas eventos solo sumamos a la lista correspondiente.
CATEGORIAS: dict[str, list[str]] = {
    "login": ["login_ok", "login_failed", "logout", "password_change"],
    "inventario": [
        "inventory_create",
        "inventory_update",
        "inventory_delete",
        "inventory_bulk_update",
    ],
    "usos": ["usage_create", "usage_delete"],
    "usuarios": ["user_create", "user_update", "user_delete"],
    "cajas": [
        "caja_create",
        "caja_revisar",
        "caja_delete",
        "instalador_create",
        "instalador_update",
        "instalador_delete",
        "herramienta_create",
        "herramienta_update",
        "herramienta_delete",
        "plantilla_create",
        "plantilla_update",
        "plantilla_delete",
    ],
}


def _parse_details(raw: str) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return raw


@router.get("", response_model=list[AuditLogOut])
def list_audit(
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    rango: str = Query("hoy", description="hoy|semana|mes|all"),
    usuario: str | None = None,
    accion: str | None = None,
    categoria: str | None = None,
    limit: int = Query(500, ge=1, le=5000),
) -> list[AuditLogOut]:
    q = db.query(AuditLog).order_by(AuditLog.ts.desc(), AuditLog.id.desc())

    # Filtro por rango de fecha. Usamos UTC porque ts se guarda en UTC;
    # esto es una aproximacion (un evento de las 23h de Honduras del dia
    # X se guarda como 5h UTC del dia X+1). Para un MVP es suficiente; el
    # frontend muestra la hora local correcta y el filtro de "hoy" en
    # general atrapa lo que el usuario espera.
    now = datetime.utcnow()
    if rango == "hoy":
        start = datetime.combine(now.date(), datetime.min.time())
        q = q.filter(AuditLog.ts >= start)
    elif rango == "semana":
        start = datetime.combine(now.date() - timedelta(days=6), datetime.min.time())
        q = q.filter(AuditLog.ts >= start)
    elif rango == "mes":
        start = datetime.combine(now.date() - timedelta(days=30), datetime.min.time())
        q = q.filter(AuditLog.ts >= start)
    # 'all': sin filtro de fecha.

    if usuario:
        q = q.filter(AuditLog.username_snapshot == usuario)
    if accion:
        q = q.filter(AuditLog.action == accion)
    if categoria and categoria in CATEGORIAS:
        q = q.filter(AuditLog.action.in_(CATEGORIAS[categoria]))

    rows = q.limit(limit).all()
    out: list[AuditLogOut] = []
    for r in rows:
        ts = ""
        if r.ts is not None:
            # Sufijo Z para que el frontend lo interprete como UTC.
            ts = r.ts.replace(microsecond=0).isoformat() + "Z"
        out.append(
            AuditLogOut(
                id=r.id,
                user_id=r.user_id,
                username=r.username_snapshot or "",
                action=r.action,
                entity_type=r.entity_type or "",
                entity_id=r.entity_id or "",
                details=_parse_details(r.details_json or ""),
                ts=ts,
            )
        )
    return out


@router.get("/categorias")
def list_categorias(
    _: Annotated[User, Depends(require_admin)],
) -> dict[str, list[str]]:
    """Devuelve el mapeo categoria -> acciones, para que el frontend
    pueda armar el filtro sin hardcodear la lista."""
    return CATEGORIAS
