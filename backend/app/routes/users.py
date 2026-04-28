"""Usuarios (solo admin)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..auth import hash_password, require_admin
from ..db import get_db
from ..models import User
from ..schemas import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> list[UserOut]:
    users = db.query(User).order_by(User.id).all()
    return [UserOut(id=u.id, username=u.username, role=u.role) for u in users]


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    actor: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> UserOut:
    existing = db.query(User).filter(User.username == payload.username).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario con ese nombre",
        )
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    write_audit(
        db,
        action="user_create",
        actor=actor,
        entity_type="user",
        entity_id=user.id,
        details={"username": user.username, "role": user.role},
    )
    return UserOut(id=user.id, username=user.username, role=user.role)


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> UserOut:
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    prev_username = target.username
    prev_role = target.role

    if payload.username is not None and payload.username != target.username:
        other = db.query(User).filter(User.username == payload.username).first()
        if other is not None and other.id != target.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe un usuario con ese nombre",
            )
        target.username = payload.username

    if payload.password:
        target.password_hash = hash_password(payload.password)

    if payload.role is not None and payload.role != target.role:
        # Evitar que el ultimo admin se quede sin rol admin.
        if target.role == "admin" and payload.role != "admin":
            remaining_admins = (
                db.query(User).filter(User.role == "admin", User.id != target.id).count()
            )
            if remaining_admins == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No se puede quitar el rol admin del ultimo administrador",
                )
        target.role = payload.role

    db.commit()
    db.refresh(target)
    changes: dict = {}
    if payload.username is not None and payload.username != prev_username:
        changes["username"] = {"before": prev_username, "after": target.username}
    if payload.role is not None and payload.role != prev_role:
        changes["role"] = {"before": prev_role, "after": target.role}
    if payload.password:
        changes["password"] = "changed"
    write_audit(
        db,
        action="user_update",
        actor=admin,
        entity_type="user",
        entity_id=target.id,
        details={"username": target.username, "changes": changes},
    )
    return UserOut(id=target.id, username=target.username, role=target.role)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    if target.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes eliminar tu propia cuenta",
        )
    if target.role == "admin":
        remaining_admins = (
            db.query(User).filter(User.role == "admin", User.id != target.id).count()
        )
        if remaining_admins == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede eliminar el ultimo administrador",
            )
    snapshot = {"username": target.username, "role": target.role}
    db.delete(target)
    db.commit()
    write_audit(
        db,
        action="user_delete",
        actor=admin,
        entity_type="user",
        entity_id=user_id,
        details=snapshot,
    )
    return None
