"""Inventario: list, create, update, delete."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import get_current_user, require_admin
from ..db import get_db
from ..models import InventoryItem, User
from ..schemas import InventoryItemIn, InventoryItemOut

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
