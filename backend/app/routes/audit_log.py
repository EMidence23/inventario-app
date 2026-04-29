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
    "inventario": [
        "inventory_create",
        "inventory_update",
        "inventory_delete",
        "inventory_bulk_update",
    ],
    "usos": ["usage_create", "usage_delete"],
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
    accesorio_code: str | None = Query(
        None,
        description=(
            "Si se envia, filtra a eventos que afectaron al accesorio con ese "
            "codigo (creacion/edicion/borrado/uso). Implica rango=all si no se "
            "especifica otro rango explicito."
        ),
    ),
    limit: int = Query(500, ge=1, le=5000),
) -> list[AuditLogOut]:
    q = db.query(AuditLog).order_by(AuditLog.ts.desc(), AuditLog.id.desc())

    # Filtro por rango de fecha. Los timestamps se guardan en UTC pero el
    # usuario piensa en hora de Honduras (UTC-6). Si calculamos "hoy" con
    # la fecha UTC, despues de las 18:00 hora Honduras la fecha UTC ya es
    # del dia siguiente y el filtro deja afuera todo lo que se hizo
    # durante el dia. Hacemos los calculos en hora local de Honduras y
    # luego convertimos los limites de vuelta a UTC.
    HN_OFFSET = timedelta(hours=-6)
    now_utc = datetime.utcnow()
    now_hn = now_utc + HN_OFFSET
    if rango == "hoy":
        start_hn = datetime.combine(now_hn.date(), datetime.min.time())
        start_utc = start_hn - HN_OFFSET  # = start_hn + 6h
        q = q.filter(AuditLog.ts >= start_utc)
    elif rango == "semana":
        start_hn = datetime.combine(now_hn.date() - timedelta(days=6), datetime.min.time())
        start_utc = start_hn - HN_OFFSET
        q = q.filter(AuditLog.ts >= start_utc)
    elif rango == "mes":
        start_hn = datetime.combine(now_hn.date() - timedelta(days=30), datetime.min.time())
        start_utc = start_hn - HN_OFFSET
        q = q.filter(AuditLog.ts >= start_utc)
    # 'all': sin filtro de fecha.

    if usuario:
        q = q.filter(AuditLog.username_snapshot == usuario)
    if accion:
        q = q.filter(AuditLog.action == accion)
    if categoria and categoria in CATEGORIAS:
        q = q.filter(AuditLog.action.in_(CATEGORIAS[categoria]))

    # Filtro por accesorio: matchea cualquier evento de inventario o uso
    # cuyo details_json mencione el codigo. La busqueda es a nivel de
    # substring del JSON crudo, suficiente porque los codigos son cortos
    # y unicos (no se confunden con otros campos). Usa parametros bindeados
    # via SQLAlchemy.like para evitar inyeccion.
    if accesorio_code:
        code = accesorio_code.strip()
        if code:
            relevantes = [
                "inventory_create",
                "inventory_update",
                "inventory_delete",
                "inventory_bulk_update",
                "usage_create",
                "usage_delete",
            ]
            q = q.filter(AuditLog.action.in_(relevantes))
            # Buscar el code como valor de la propiedad "code" en el JSON.
            # Las dos formas que aparecen en los detalles:
            #   "code":"NB-ER04-TL600"   (inventory create/update/delete + sample bulk + items uso)
            # Cubrimos ambas y dejamos que SQLite haga el match.
            like_pattern = f'%"code": "{code}"%'
            like_pattern2 = f'%"code":"{code}"%'  # por si algun dump no tiene espacio.
            q = q.filter(
                (AuditLog.details_json.like(like_pattern))
                | (AuditLog.details_json.like(like_pattern2))
            )

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
