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
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[InventoryItemOut]:
    rows = db.query(InventoryItem).order_by(InventoryItem.id).all()
    return [InventoryItemOut(id=r.id, code=r.code, name=r.name, cat=r.cat or "") for r in rows]


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
    item = InventoryItem(code=payload.code, name=payload.name, cat=payload.cat or "")
    db.add(item)
    db.commit()
    db.refresh(item)
    return InventoryItemOut(id=item.id, code=item.code, name=item.name, cat=item.cat or "")


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
    db.commit()
    db.refresh(item)
    return InventoryItemOut(id=item.id, code=item.code, name=item.name, cat=item.cat or "")


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
