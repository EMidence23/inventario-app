"""Caja de Herramientas de Instaladores.

Incluye CRUD para:
- Catalogo de instaladores (tecnicos que van a obra)
- Catalogo de herramientas (distinto del inventario de 743 accesorios)
- Cajas de herramienta entregadas en el dia a un grupo de instaladores,
  con revision de devueltas/faltantes al regreso.

Acceso: admin y empleado.
"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..db import get_db
from ..models import (
    CajaHerramienta,
    CajaInstalador,
    CajaItem,
    Herramienta,
    Instalador,
    User,
)
from ..schemas import (
    CajaHerramientaIn,
    CajaHerramientaOut,
    CajaItemOut,
    CajaRevisionIn,
    HerramientaIn,
    HerramientaOut,
    InstaladorIn,
    InstaladorOut,
)


router = APIRouter(tags=["cajas"])


# ── Instaladores ───────────────────────────────────────────────
@router.get("/api/instaladores", response_model=list[InstaladorOut])
def list_instaladores(
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[InstaladorOut]:
    rows = db.query(Instalador).order_by(Instalador.nombre).all()
    return [InstaladorOut(id=r.id, nombre=r.nombre, activo=bool(r.activo)) for r in rows]


@router.post("/api/instaladores", response_model=InstaladorOut, status_code=status.HTTP_201_CREATED)
def create_instalador(
    payload: InstaladorIn,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> InstaladorOut:
    nombre = payload.nombre.strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="Nombre requerido")
    existing = db.query(Instalador).filter(Instalador.nombre == nombre).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Ya existe un instalador con ese nombre")
    row = Instalador(nombre=nombre, activo=payload.activo)
    db.add(row)
    db.commit()
    db.refresh(row)
    return InstaladorOut(id=row.id, nombre=row.nombre, activo=bool(row.activo))


@router.put("/api/instaladores/{inst_id}", response_model=InstaladorOut)
def update_instalador(
    inst_id: int,
    payload: InstaladorIn,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> InstaladorOut:
    row = db.get(Instalador, inst_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Instalador no encontrado")
    nombre = payload.nombre.strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="Nombre requerido")
    dupe = (
        db.query(Instalador)
        .filter(Instalador.nombre == nombre, Instalador.id != inst_id)
        .first()
    )
    if dupe is not None:
        raise HTTPException(status_code=409, detail="Ya existe otro instalador con ese nombre")
    row.nombre = nombre
    row.activo = payload.activo
    db.commit()
    db.refresh(row)
    return InstaladorOut(id=row.id, nombre=row.nombre, activo=bool(row.activo))


@router.delete("/api/instaladores/{inst_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_instalador(
    inst_id: int,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    row = db.get(Instalador, inst_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Instalador no encontrado")
    db.delete(row)
    db.commit()
    return None


# ── Herramientas ───────────────────────────────────────────────
@router.get("/api/herramientas", response_model=list[HerramientaOut])
def list_herramientas(
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[HerramientaOut]:
    rows = db.query(Herramienta).order_by(Herramienta.nombre).all()
    return [HerramientaOut(id=r.id, nombre=r.nombre, activo=bool(r.activo)) for r in rows]


@router.post("/api/herramientas", response_model=HerramientaOut, status_code=status.HTTP_201_CREATED)
def create_herramienta(
    payload: HerramientaIn,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> HerramientaOut:
    nombre = payload.nombre.strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="Nombre requerido")
    existing = db.query(Herramienta).filter(Herramienta.nombre == nombre).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Ya existe una herramienta con ese nombre")
    row = Herramienta(nombre=nombre, activo=payload.activo)
    db.add(row)
    db.commit()
    db.refresh(row)
    return HerramientaOut(id=row.id, nombre=row.nombre, activo=bool(row.activo))


@router.put("/api/herramientas/{h_id}", response_model=HerramientaOut)
def update_herramienta(
    h_id: int,
    payload: HerramientaIn,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> HerramientaOut:
    row = db.get(Herramienta, h_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Herramienta no encontrada")
    nombre = payload.nombre.strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="Nombre requerido")
    dupe = (
        db.query(Herramienta)
        .filter(Herramienta.nombre == nombre, Herramienta.id != h_id)
        .first()
    )
    if dupe is not None:
        raise HTTPException(status_code=409, detail="Ya existe otra herramienta con ese nombre")
    row.nombre = nombre
    row.activo = payload.activo
    db.commit()
    db.refresh(row)
    return HerramientaOut(id=row.id, nombre=row.nombre, activo=bool(row.activo))


@router.delete("/api/herramientas/{h_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_herramienta(
    h_id: int,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    row = db.get(Herramienta, h_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Herramienta no encontrada")
    # Si ya se uso en alguna caja, mejor no borrar para no romper historial.
    used = db.query(CajaItem).filter(CajaItem.herramienta_id == h_id).first()
    if used is not None:
        raise HTTPException(
            status_code=409,
            detail="No se puede borrar: esta herramienta ya se usa en cajas registradas",
        )
    db.delete(row)
    db.commit()
    return None


# ── Cajas ──────────────────────────────────────────────────────
def _caja_to_out(caja: CajaHerramienta) -> CajaHerramientaOut:
    items_out = [
        CajaItemOut(
            id=it.id,
            herramienta_id=it.herramienta_id,
            herramienta_nombre=it.herramienta_nombre_snapshot or "",
            cantidad_entregada=int(it.cantidad_entregada or 0),
            cantidad_devuelta=int(it.cantidad_devuelta or 0),
            estado=it.estado or "pendiente",
        )
        for it in caja.items
    ]
    instaladores_out = [ci.instalador_nombre_snapshot or "" for ci in caja.instaladores]
    total_ent = sum(i.cantidad_entregada for i in items_out)
    total_dev = sum(i.cantidad_devuelta for i in items_out)
    total_falt = max(0, total_ent - total_dev)
    if caja.hora_revision is None:
        estado_caja = "pendiente"
    elif total_falt == 0:
        estado_caja = "completa"
    else:
        estado_caja = "faltante"
    return CajaHerramientaOut(
        id=caja.id,
        fecha=caja.fecha,
        hora_entrega=caja.hora_entrega.isoformat() if caja.hora_entrega else "",
        creada_por=caja.creada_por_username or "",
        revisada_por=caja.revisada_por_username or None,
        hora_revision=caja.hora_revision.isoformat() if caja.hora_revision else None,
        instaladores=instaladores_out,
        items=items_out,
        total_entregadas=total_ent,
        total_devueltas=total_dev,
        total_faltantes=total_falt,
        estado=estado_caja,
        notas=caja.notas or "",
    )


@router.get("/api/cajas", response_model=list[CajaHerramientaOut])
def list_cajas(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[CajaHerramientaOut]:
    rows = (
        db.query(CajaHerramienta)
        .order_by(CajaHerramienta.fecha.desc(), CajaHerramienta.id.desc())
        .all()
    )
    return [_caja_to_out(r) for r in rows]


@router.post("/api/cajas", response_model=CajaHerramientaOut, status_code=status.HTTP_201_CREATED)
def create_caja(
    payload: CajaHerramientaIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CajaHerramientaOut:
    # Fecha: si no viene, usar hoy UTC (el frontend la manda segun local).
    fecha = payload.fecha or datetime.utcnow().strftime("%Y-%m-%d")

    # Validar instaladores.
    inst_rows = (
        db.query(Instalador).filter(Instalador.id.in_(payload.instalador_ids)).all()
    )
    if len(inst_rows) != len(set(payload.instalador_ids)):
        raise HTTPException(status_code=400, detail="Uno o mas instaladores no existen")

    # Validar herramientas y cantidades.
    h_ids = [it.herramienta_id for it in payload.items]
    if len(h_ids) != len(set(h_ids)):
        raise HTTPException(status_code=400, detail="Herramientas duplicadas en la caja")
    h_rows = db.query(Herramienta).filter(Herramienta.id.in_(h_ids)).all()
    if len(h_rows) != len(h_ids):
        raise HTTPException(status_code=400, detail="Una o mas herramientas no existen")
    h_by_id = {h.id: h for h in h_rows}
    for it in payload.items:
        if it.cantidad_entregada <= 0:
            raise HTTPException(
                status_code=400,
                detail=f"La cantidad entregada de '{h_by_id[it.herramienta_id].nombre}' debe ser mayor a 0",
            )

    caja = CajaHerramienta(
        fecha=fecha,
        hora_entrega=datetime.utcnow(),
        creada_por_user_id=user.id,
        creada_por_username=user.username,
        notas=(payload.notas or "").strip(),
    )
    db.add(caja)
    db.flush()

    for inst in inst_rows:
        db.add(
            CajaInstalador(
                caja_id=caja.id,
                instalador_id=inst.id,
                instalador_nombre_snapshot=inst.nombre,
            )
        )

    for it in payload.items:
        h = h_by_id[it.herramienta_id]
        db.add(
            CajaItem(
                caja_id=caja.id,
                herramienta_id=h.id,
                herramienta_nombre_snapshot=h.nombre,
                cantidad_entregada=int(it.cantidad_entregada),
                cantidad_devuelta=0,
                estado="pendiente",
            )
        )

    db.commit()
    db.refresh(caja)
    return _caja_to_out(caja)


@router.post("/api/cajas/{caja_id}/revisar", response_model=CajaHerramientaOut)
def revisar_caja(
    caja_id: int,
    payload: CajaRevisionIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CajaHerramientaOut:
    caja = db.get(CajaHerramienta, caja_id)
    if caja is None:
        raise HTTPException(status_code=404, detail="Caja no encontrada")

    by_id = {it.id: it for it in caja.items}
    seen: set[int] = set()
    for rev in payload.items:
        if rev.id not in by_id:
            raise HTTPException(
                status_code=400,
                detail=f"Item {rev.id} no pertenece a esta caja",
            )
        item = by_id[rev.id]
        if rev.cantidad_devuelta > item.cantidad_entregada:
            raise HTTPException(
                status_code=400,
                detail=f"Devueltas ({rev.cantidad_devuelta}) no puede superar entregadas ({item.cantidad_entregada}) en '{item.herramienta_nombre_snapshot}'",
            )
        item.cantidad_devuelta = int(rev.cantidad_devuelta)
        item.estado = "devuelta" if item.cantidad_devuelta >= item.cantidad_entregada else "faltante"
        seen.add(rev.id)

    # Los items que no se mandaron quedan como estaban (permite revision parcial
    # pero al marcarla como revisada los pendientes se asumen faltantes).
    for item in caja.items:
        if item.id not in seen and item.estado == "pendiente":
            item.estado = "devuelta" if item.cantidad_devuelta >= item.cantidad_entregada else "faltante"

    caja.revisada_por_user_id = user.id
    caja.revisada_por_username = user.username
    caja.hora_revision = datetime.utcnow()
    if payload.notas is not None:
        caja.notas = payload.notas.strip()

    db.commit()
    db.refresh(caja)
    return _caja_to_out(caja)


@router.delete("/api/cajas/{caja_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_caja(
    caja_id: int,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    caja = db.get(CajaHerramienta, caja_id)
    if caja is None:
        raise HTTPException(status_code=404, detail="Caja no encontrada")
    db.delete(caja)
    db.commit()
    return None
