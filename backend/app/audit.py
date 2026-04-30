"""Helper centralizado para escribir entradas en la bitacora.

El patron es un solo entrypoint `write_audit(db, action, ...)` que:
- Captura el usuario actual (si lo hay) en username_snapshot.
- Serializa los detalles a JSON.
- NUNCA permite que un fallo al loggear tumbe la operacion principal:
  cualquier excepcion al insertar el log se atrapa silenciosamente
  (la bitacora es valor-agregado, no debe romper la API).
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from .models import AuditLog, User


def write_audit(
    db: Session,
    *,
    action: str,
    actor: User | None = None,
    actor_username: str | None = None,
    entity_type: str = "",
    entity_id: str | int = "",
    details: dict[str, Any] | None = None,
) -> None:
    """Inserta una entrada en la bitacora.

    Soporta dos formas de identificar al autor:
    - actor: el objeto User (el caso comun, viene de get_current_user).
    - actor_username: solo el username (login fallido, donde no hay User).
    """
    try:
        user_id: int | None = None
        username = ""
        if actor is not None:
            user_id = actor.id
            username = actor.username
        elif actor_username is not None:
            username = actor_username

        details_str = ""
        if details:
            try:
                details_str = json.dumps(details, ensure_ascii=False, default=str)
            except (TypeError, ValueError):
                details_str = json.dumps({"raw": str(details)})

        entry = AuditLog(
            user_id=user_id,
            username_snapshot=username[:80],
            action=action[:48],
            entity_type=str(entity_type)[:32],
            entity_id=str(entity_id)[:48],
            details_json=details_str,
        )
        db.add(entry)
        db.commit()
    except Exception:
        # Nunca fallar la peticion principal por un error de logging.
        try:
            db.rollback()
        except Exception:
            pass
