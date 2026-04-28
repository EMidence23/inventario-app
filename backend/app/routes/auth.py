"""Auth endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from ..db import get_db
from ..models import User
from ..schemas import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    UserOut,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> LoginResponse:
    user = db.query(User).filter(User.username == payload.username).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        write_audit(
            db,
            action="login_failed",
            actor_username=payload.username,
            details={"reason": "user_not_found" if user is None else "bad_password"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contrasena incorrectos",
        )
    token = create_access_token(user.id)
    write_audit(db, action="login_ok", actor=user, details={"role": user.role})
    return LoginResponse(
        access_token=token,
        user=UserOut(id=user.id, username=user.username, role=user.role),
    )


@router.get("/me", response_model=UserOut)
def me(user: Annotated[User, Depends(get_current_user)]) -> UserOut:
    return UserOut(id=user.id, username=user.username, role=user.role)


@router.post("/change-password", response_model=UserOut)
def change_password(
    payload: ChangePasswordRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> UserOut:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contrasena actual es incorrecta",
        )
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    db.refresh(user)
    write_audit(db, action="password_change", actor=user)
    return UserOut(id=user.id, username=user.username, role=user.role)


@router.post("/logout")
def logout(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, bool]:
    """Logout es solo trazabilidad: el JWT es stateless, asi que no se
    invalida del lado del servidor. Sirve para que la bitacora registre
    cuando el usuario cerro sesion explicitamente."""
    write_audit(db, action="logout", actor=user)
    return {"ok": True}
