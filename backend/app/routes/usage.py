"""Registros de uso diario."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..auth import get_current_user, require_admin
from ..db import get_db
from ..models import InventoryItem, UsageRecord, User
from ..schemas import (
    UsageItemOut,
    UsageRecordIn,
    UsageRecordOut,
)

router = APIRouter(prefix="/api/usage", tags=["usage"])

# Honduras esta en UTC-6. El servidor corre en UTC asi que para calcular
# "hoy" en hora local sumamos el offset.
_HN_OFFSET = timedelta(hours=-6)


def _to_out(row: UsageRecord) -> UsageRecordOut:
    items_data = json.loads(row.items_json or "[]")
    items = [
        UsageItemOut(
            id=int(it.get("id", 0)),
            code=str(it.get("code", "")),
            name=str(it.get("name", "")),
            qtyUsed=int(it.get("qtyUsed", 0)),
            unit_cost=float(it.get("unit_cost") or 0.0),
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
    # Validar PRIMERO que cada item.id exista en inventario. Si alguno no
    # existe, abortamos todo el registro y devolvemos 400 — evita registros
    # "fantasma" que aparezcan en HISTORIAL sin haber descontado stock real.
    missing: list[str] = []
    for it in filtered:
        if db.get(InventoryItem, it.id) is None:
            missing.append(f"{it.code or '?'} (id {it.id})")
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Accesorio(s) no existen en inventario: " + ", ".join(missing),
        )
    now = datetime.utcnow()
    # Preferir la fecha local del cliente cuando viene en el payload; evita
    # que registros creados cerca de medianoche UTC caigan en el dia
    # "equivocado" para usuarios en zonas horarias distintas de UTC. El
    # fallback usa hora Honduras (UTC-6) para que clientes externos sin
    # 'date' tampoco caigan en el dia siguiente despues de las 18:00 local.
    local_date = payload.date or (now + _HN_OFFSET).strftime("%Y-%m-%d")
    record = UsageRecord(
        user_id=user.id,
        username_snapshot=user.username,
        date=local_date,
        ts=now,
        items_json="[]",
    )
    # Descontar el uso del stock de cada accesorio. Para evitar race
    # conditions cuando dos clientes registran uso del mismo accesorio al
    # mismo tiempo: usamos UPDATE atomico con WHERE stock>=0 y RETURNING
    # del nuevo stock, para que cada cliente vea el valor real post-update
    # y no sobreescriba el descuento del otro. SQLite serializa escrituras
    # a la misma fila, asi que el segundo UPDATE espera al primero.
    from sqlalchemy import text

    persisted_items = []
    for it in filtered:
        inv = db.get(InventoryItem, it.id)
        if inv is None:
            # Ya validado arriba; defensivo por si el item se borra entre
            # la validacion y aqui (ventana muy corta).
            continue
        # Re-leer stock fresco con bloqueo (FOR UPDATE en backends que lo
        # soporten; en SQLite cae a un lock implicito de la fila al
        # actualizar). Refresh fuerza una nueva lectura desde la BD.
        db.refresh(inv)
        available = inv.stock or 0
        actual = max(0, min(it.qtyUsed, available))
        unit_cost = float(inv.cost or 0.0)
        new_stock = available - actual
        # Update atomico que solo aplica si el stock no cambio entre el
        # refresh y este UPDATE (compare-and-swap). Si otro cliente nos
        # gano la carrera, reintentamos hasta 5 veces leyendo de nuevo.
        for _attempt in range(5):
            res = db.execute(
                text(
                    "UPDATE inventory_items SET stock = :new_stock "
                    "WHERE id = :id AND stock = :expected"
                ),
                {"new_stock": new_stock, "id": inv.id, "expected": available},
            )
            if res.rowcount == 1:
                break
            # Otro cliente cambio el stock. Releemos y recalculamos.
            db.refresh(inv)
            available = inv.stock or 0
            actual = max(0, min(it.qtyUsed, available))
            new_stock = available - actual
        else:
            # Despues de 5 reintentos seguimos sin lograr el update; raro,
            # pero por seguridad usamos lo que tengamos.
            inv.stock = new_stock
        # Sincronizar el objeto en memoria con el valor que escribimos.
        inv.stock = new_stock
        data = it.model_dump()
        data["actualDeducted"] = actual
        data["unit_cost"] = unit_cost
        # Snapshot de stock antes/despues solo para el audit. No se
        # persiste en items_json del UsageRecord para no inflar la
        # respuesta del HISTORIAL — basta con verlo en MOVIMIENTOS.
        data["_stock_before"] = available
        data["_stock_after"] = new_stock
        persisted_items.append(data)
    # items_json del registro NO debe incluir los snapshots de stock
    # (son ruido para HISTORIAL). Los retiramos aqui antes de guardar.
    items_to_save = [
        {k: v for k, v in d.items() if not k.startswith("_")}
        for d in persisted_items
    ]
    record.items_json = json.dumps(items_to_save)
    db.add(record)
    db.commit()
    db.refresh(record)
    write_audit(
        db,
        action="usage_create",
        actor=user,
        entity_type="usage_record",
        entity_id=record.id,
        details={
            "date": record.date,
            "items": [
                {
                    "code": it.get("code", ""),
                    "name": it.get("name", ""),
                    "qtyUsed": int(it.get("qtyUsed", 0)),
                    "actualDeducted": int(it.get("actualDeducted", 0)),
                    "stock_before": int(it.get("_stock_before", 0)),
                    "stock_after": int(it.get("_stock_after", 0)),
                }
                for it in persisted_items
            ],
        },
    )
    return _to_out(record)


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_usage(
    record_id: int,
    actor: Annotated[User, Depends(require_admin)],
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
    audit_items = []
    for it in items_data:
        try:
            inv_id = int(it.get("id", 0))
            # Preferir 'actualDeducted' (cantidad realmente descontada del stock)
            # para no inflar el stock cuando el qtyUsed original fue mayor al
            # stock disponible. Fallback a qtyUsed para registros viejos.
            if "actualDeducted" in it:
                qty = int(it.get("actualDeducted", 0))
            else:
                qty = int(it.get("qtyUsed", 0))
        except (TypeError, ValueError):
            continue
        if not inv_id or qty <= 0:
            continue
        inv = db.get(InventoryItem, inv_id)
        if inv is None:
            continue
        inv.stock = (inv.stock or 0) + qty
        audit_items.append({
            "code": str(it.get("code", "")),
            "name": str(it.get("name", "")),
            "restored": qty,
        })
    snapshot = {
        "date": row.date,
        "original_user": row.username_snapshot or "",
        "items_restored": audit_items,
    }
    db.delete(row)
    db.commit()
    write_audit(
        db,
        action="usage_delete",
        actor=actor,
        entity_type="usage_record",
        entity_id=record_id,
        details=snapshot,
    )
    return None
