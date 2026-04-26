"""Inventario: list, create, update, delete."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import get_current_user, require_admin
from ..db import get_db
from ..models import InventoryItem, User
from ..schemas import (
    InventoryBulkIn,
    InventoryBulkOut,
    InventoryBulkResultRow,
    InventoryItemIn,
    InventoryItemOut,
)

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


@router.get("", response_model=list[InventoryItemOut])
def list_items(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[InventoryItemOut]:
    rows = db.query(InventoryItem).order_by(InventoryItem.id).all()
    # El costo unitario es informacion sensible (margenes); solo lo
    # devolvemos al admin. Para empleados se esconde a 0 desde la API
    # para que ni siquiera con devtools se pueda leer.
    expose_cost = user.role == "admin"
    return [
        InventoryItemOut(
            id=r.id,
            code=r.code,
            name=r.name,
            cat=r.cat or "",
            stock=r.stock or 0,
            cost=float(r.cost or 0.0) if expose_cost else 0.0,
        )
        for r in rows
    ]


@router.post("", response_model=InventoryItemOut, status_code=status.HTTP_201_CREATED)
def create_item(
    payload: InventoryItemIn,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> InventoryItemOut:
    if db.query(InventoryItem).filter(InventoryItem.code == payload.code).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un accesorio con ese codigo",
        )
    item = InventoryItem(
        code=payload.code,
        name=payload.name,
        cat=payload.cat or "",
        stock=payload.stock if payload.stock is not None else 0,
        cost=float(payload.cost) if payload.cost is not None else 0.0,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return InventoryItemOut(
        id=item.id,
        code=item.code,
        name=item.name,
        cat=item.cat or "",
        stock=item.stock or 0,
        cost=float(item.cost or 0.0),
    )


@router.put("/{item_id}", response_model=InventoryItemOut)
def update_item(
    item_id: int,
    payload: InventoryItemIn,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> InventoryItemOut:
    item = db.get(InventoryItem, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Accesorio no encontrado")
    other = (
        db.query(InventoryItem)
        .filter(InventoryItem.code == payload.code, InventoryItem.id != item_id)
        .first()
    )
    if other is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe otro accesorio con ese codigo",
        )
    item.code = payload.code
    item.name = payload.name
    item.cat = payload.cat or ""
    if payload.stock is not None:
        item.stock = payload.stock
    if payload.cost is not None:
        item.cost = float(payload.cost)
    db.commit()
    db.refresh(item)
    return InventoryItemOut(
        id=item.id,
        code=item.code,
        name=item.name,
        cat=item.cat or "",
        stock=item.stock or 0,
        cost=float(item.cost or 0.0),
    )


@router.post("/bulk-update", response_model=InventoryBulkOut)
def bulk_update(
    payload: InventoryBulkIn,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> InventoryBulkOut:
    """Actualizacion masiva desde Excel.

    El frontend parsea el Excel y envia las filas normalizadas aqui. Con
    commit=False solo calculamos el diff (preview); con commit=True se
    aplican los cambios dentro de una transaccion unica.

    Reglas:
    - code es obligatorio. Si el code no existe en la BD -> skipped_not_found
      (no se crean productos nuevos desde aqui, es seguro contra typos).
    - stock / cost_with_isv / name / cat son opcionales: si la celda vino
      vacia, NO se toca el campo del producto.
    - El costo viene CON ISV y se guarda SIN ISV (cost = cost_with_isv / (1+isv_rate)).
    """
    results: list[InventoryBulkResultRow] = []
    would_update = 0
    not_found = 0
    no_changes = 0
    invalid = 0

    # Pre-cargar productos por code para evitar N queries.
    codes = list({r.code.strip() for r in payload.rows if r.code and r.code.strip()})
    items_by_code = {
        it.code: it
        for it in db.query(InventoryItem).filter(InventoryItem.code.in_(codes)).all()
    }

    isv_divisor = 1.0 + (payload.isv_rate or 0.0)
    seen_codes: set[str] = set()

    for row in payload.rows:
        code = (row.code or "").strip()
        if not code:
            invalid += 1
            results.append(
                InventoryBulkResultRow(
                    code="",
                    action="invalid",
                    changes=[],
                    reason="Fila sin CodProducto",
                )
            )
            continue
        if code in seen_codes:
            invalid += 1
            results.append(
                InventoryBulkResultRow(
                    code=code,
                    action="invalid",
                    changes=[],
                    reason="CodProducto duplicado en el archivo",
                )
            )
            continue
        seen_codes.add(code)

        item = items_by_code.get(code)
        if item is None:
            not_found += 1
            results.append(
                InventoryBulkResultRow(
                    code=code,
                    action="skipped_not_found",
                    changes=[],
                    reason="No existe un producto con ese CodProducto",
                )
            )
            continue

        changes: list[str] = []
        new_stock = item.stock
        new_cost = float(item.cost or 0.0)
        new_name = item.name
        new_cat = item.cat or ""

        if row.stock is not None and int(row.stock) != (item.stock or 0):
            new_stock = int(row.stock)
            changes.append(f"stock: {item.stock or 0} -> {new_stock}")

        if row.cost_with_isv is not None:
            # Redondear a 4 decimales para comparaciones estables.
            computed = round(float(row.cost_with_isv) / isv_divisor, 4)
            current = round(float(item.cost or 0.0), 4)
            if abs(computed - current) > 0.005:
                new_cost = computed
                changes.append(
                    f"costo s/ISV: L. {current:.2f} -> L. {computed:.2f}"
                )

        if row.name is not None:
            nn = row.name.strip()
            if nn and nn != (item.name or ""):
                new_name = nn
                changes.append("descripcion actualizada")

        if row.cat is not None:
            nc = row.cat.strip()
            if nc != (item.cat or ""):
                new_cat = nc
                changes.append(
                    f"categoria: '{item.cat or ''}' -> '{nc}'"
                )

        if not changes:
            no_changes += 1
            results.append(
                InventoryBulkResultRow(
                    code=code, action="skipped_no_changes", changes=[]
                )
            )
            continue

        would_update += 1
        results.append(
            InventoryBulkResultRow(code=code, action="updated", changes=changes)
        )

        if payload.commit:
            item.stock = new_stock
            item.cost = new_cost
            item.name = new_name
            item.cat = new_cat

    if payload.commit:
        db.commit()

    return InventoryBulkOut(
        total_rows=len(payload.rows),
        would_update=would_update,
        not_found=not_found,
        no_changes=no_changes,
        invalid=invalid,
        committed=payload.commit,
        results=results,
    )


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    item_id: int,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    item = db.get(InventoryItem, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Accesorio no encontrado")
    db.delete(item)
    db.commit()
    return None
