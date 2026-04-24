"""Registros de uso diario."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import get_current_user, require_admin
from ..db import get_db
from ..models import InventoryItem, UsageRecord, User
from ..schemas import (
    UsageItemOut,
    UsageRecordIn,
    UsageRecordOut,
)

router = APIRouter(prefix="/api/usage", tags=["usage"])


def _to_out(row: UsageRecord) -> UsageRecordOut:
    items_data = json.loads(row.items_json or "[]")
    items = [
        UsageItemOut(
            id=int(it.get("id", 0)),
            code=str(it.get("code", "")),
            name=str(it.get("name", "")),
            qtyUsed=int(it.get("qtyUsed", 0)),
        )
        for it in items_data
    ]
    # Los timestamps se guardan con datetime.utcnow(); anadimos el sufijo 'Z'
    # para que el frontend los interprete como UTC en lugar de hora local.
    ts = (row.ts.isoformat() + "Z") if row.ts else ""
    return UsageRecordOut(
        id=row.id,
        user=row.username_snapshot or "",
        date=row.date,
        ts=ts,
        items=items,
    )


@router.get("", response_model=list[UsageRecordOut])
def list_usage(
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[UsageRecordOut]:
    rows = db.query(UsageRecord).order_by(UsageRecord.id).all()
    return [_to_out(r) for r in rows]


@router.post("", response_model=UsageRecordOut, status_code=status.HTTP_201_CREATED)
def create_usage(
    payload: UsageRecordIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> UsageRecordOut:
    filtered = [it for it in payload.items if it.qtyUsed > 0]
    if not filtered:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ingresa al menos 1 accesorio usado",
        )
    now = datetime.utcnow()
    # Preferir la fecha local del cliente cuando viene en el payload; evita
    # que registros creados cerca de medianoche UTC caigan en el dia
    # "equivocado" para usuarios en zonas horarias distintas de UTC.
    local_date = payload.date or now.strftime("%Y-%m-%d")
    record = UsageRecord(
        user_id=user.id,
        username_snapshot=user.username,
        date=local_date,
        ts=now,
        items_json=json.dumps([it.model_dump() for it in filtered]),
    )
    db.add(record)
    # Descontar el uso del stock de cada accesorio. Si el producto no existe
    # (p.ej. fue borrado) solo ignoramos. El stock puede quedar en 0 pero no
    # se vuelve negativo.
    for it in filtered:
        inv = db.get(InventoryItem, it.id)
        if inv is None:
            continue
        inv.stock = max(0, (inv.stock or 0) - it.qtyUsed)
    db.commit()
    db.refresh(record)
    return _to_out(record)


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_usage(
    record_id: int,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    row = db.get(UsageRecord, record_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registro no encontrado")
    # Devolver el uso al stock de cada accesorio antes de borrar el registro.
    try:
        items_data = json.loads(row.items_json or "[]")
    except (TypeError, ValueError):
        items_data = []
    for it in items_data:
        try:
            inv_id = int(it.get("id", 0))
            qty = int(it.get("qtyUsed", 0))
        except (TypeError, ValueError):
            continue
        if not inv_id or qty <= 0:
            continue
        inv = db.get(InventoryItem, inv_id)
        if inv is None:
            continue
        inv.stock = (inv.stock or 0) + qty
    db.delete(row)
    db.commit()
    return None
