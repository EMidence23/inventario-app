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

from ..audit import write_audit
from ..auth import get_current_user, require_admin
from ..db import get_db
from ..models import (
    CajaHerramienta,
    CajaInstalador,
    CajaItem,
    CajaPlantilla,
    CajaPlantillaItem,
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
    PlantillaIn,
    PlantillaItemOut,
    PlantillaOut,
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
    actor: Annotated[User, Depends(get_current_user)],
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
    write_audit(db, action="instalador_create", actor=actor, entity_type="instalador", entity_id=row.id, details={"nombre": row.nombre, "activo": bool(row.activo)})
    return InstaladorOut(id=row.id, nombre=row.nombre, activo=bool(row.activo))


@router.put("/api/instaladores/{inst_id}", response_model=InstaladorOut)
def update_instalador(
    inst_id: int,
    payload: InstaladorIn,
    actor: Annotated[User, Depends(get_current_user)],
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
    prev = {"nombre": row.nombre, "activo": bool(row.activo)}
    row.nombre = nombre
    row.activo = payload.activo
    db.commit()
    db.refresh(row)
    write_audit(db, action="instalador_update", actor=actor, entity_type="instalador", entity_id=row.id, details={"before": prev, "after": {"nombre": row.nombre, "activo": bool(row.activo)}})
    return InstaladorOut(id=row.id, nombre=row.nombre, activo=bool(row.activo))


@router.delete("/api/instaladores/{inst_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_instalador(
    inst_id: int,
    actor: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    row = db.get(Instalador, inst_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Instalador no encontrado")
    snapshot = {"nombre": row.nombre, "activo": bool(row.activo)}
    db.delete(row)
    db.commit()
    write_audit(db, action="instalador_delete", actor=actor, entity_type="instalador", entity_id=inst_id, details=snapshot)
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
    actor: Annotated[User, Depends(get_current_user)],
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
    write_audit(db, action="herramienta_create", actor=actor, entity_type="herramienta", entity_id=row.id, details={"nombre": row.nombre, "activo": bool(row.activo)})
    return HerramientaOut(id=row.id, nombre=row.nombre, activo=bool(row.activo))


@router.put("/api/herramientas/{h_id}", response_model=HerramientaOut)
def update_herramienta(
    h_id: int,
    payload: HerramientaIn,
    actor: Annotated[User, Depends(get_current_user)],
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
    prev = {"nombre": row.nombre, "activo": bool(row.activo)}
    row.nombre = nombre
    row.activo = payload.activo
    db.commit()
    db.refresh(row)
    write_audit(db, action="herramienta_update", actor=actor, entity_type="herramienta", entity_id=row.id, details={"before": prev, "after": {"nombre": row.nombre, "activo": bool(row.activo)}})
    return HerramientaOut(id=row.id, nombre=row.nombre, activo=bool(row.activo))


@router.delete("/api/herramientas/{h_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_herramienta(
    h_id: int,
    actor: Annotated[User, Depends(get_current_user)],
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
    # Tampoco permitir borrar si esta referenciada en alguna plantilla;
    # el FK es ondelete=RESTRICT y romperia con un IntegrityError 500.
    in_plantilla = (
        db.query(CajaPlantillaItem).filter(CajaPlantillaItem.herramienta_id == h_id).first()
    )
    if in_plantilla is not None:
        raise HTTPException(
            status_code=409,
            detail="No se puede borrar: esta herramienta esta en una o mas plantillas. Quitala de las plantillas primero.",
        )
    snapshot = {"nombre": row.nombre, "activo": bool(row.activo)}
    db.delete(row)
    db.commit()
    write_audit(db, action="herramienta_delete", actor=actor, entity_type="herramienta", entity_id=h_id, details=snapshot)
    return None


# ── Cajas ──────────────────────────────────────────────────────
def _iso_utc(dt: datetime | None) -> str | None:
    """Devuelve ISO con sufijo Z para que el frontend lo interprete como UTC
    y lo convierta a hora local. Nuestros datetimes se guardan con
    datetime.utcnow(), asi que son siempre UTC aunque sean naive."""
    if dt is None:
        return None
    return dt.replace(microsecond=0).isoformat() + "Z"


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
        hora_entrega=_iso_utc(caja.hora_entrega) or "",
        creada_por=caja.creada_por_username or "",
        revisada_por=caja.revisada_por_username or None,
        hora_revision=_iso_utc(caja.hora_revision),
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
    rango: str = "all",
) -> list[CajaHerramientaOut]:
    """Lista cajas.

    Admin: puede filtrar por rango=hoy|semana|all (default all, historial completo).
    Empleado: siempre ve solo las cajas de HOY, ignora el parametro rango.
    """
    from datetime import date, timedelta

    q = db.query(CajaHerramienta).order_by(
        CajaHerramienta.fecha.desc(), CajaHerramienta.id.desc()
    )

    today = date.today().isoformat()
    if user.role != "admin":
        # Empleado: siempre ve solo hoy (el historial es solo-admin).
        q = q.filter(CajaHerramienta.fecha == today)
    else:
        if rango == "hoy":
            q = q.filter(CajaHerramienta.fecha == today)
        elif rango == "semana":
            # Semana corrida: hoy y los 6 dias anteriores.
            hace7 = (date.today() - timedelta(days=6)).isoformat()
            q = q.filter(CajaHerramienta.fecha >= hace7)
        # rango 'all' (default) o desconocido: sin filtro de fecha.

    return [_caja_to_out(r) for r in q.all()]


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
    write_audit(
        db,
        action="caja_create",
        actor=user,
        entity_type="caja",
        entity_id=caja.id,
        details={
            "fecha": caja.fecha,
            "instaladores": [i.nombre for i in inst_rows],
            "items": [{"herramienta": h_by_id[it.herramienta_id].nombre, "entregadas": int(it.cantidad_entregada)} for it in payload.items],
            "notas": caja.notas or "",
        },
    )
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
    total_ent = sum(int(it.cantidad_entregada or 0) for it in caja.items)
    total_dev = sum(int(it.cantidad_devuelta or 0) for it in caja.items)
    write_audit(
        db,
        action="caja_revisar",
        actor=user,
        entity_type="caja",
        entity_id=caja.id,
        details={
            "fecha": caja.fecha,
            "total_entregadas": total_ent,
            "total_devueltas": total_dev,
            "total_faltantes": max(0, total_ent - total_dev),
            "items": [{"herramienta": it.herramienta_nombre_snapshot, "entregadas": int(it.cantidad_entregada or 0), "devueltas": int(it.cantidad_devuelta or 0), "estado": it.estado} for it in caja.items],
        },
    )
    return _caja_to_out(caja)


@router.delete("/api/cajas/{caja_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_caja(
    caja_id: int,
    actor: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    # Solo admin puede borrar del historial.
    caja = db.get(CajaHerramienta, caja_id)
    if caja is None:
        raise HTTPException(status_code=404, detail="Caja no encontrada")
    snapshot = {
        "fecha": caja.fecha,
        "creada_por": caja.creada_por_username,
        "instaladores": [ci.instalador_nombre_snapshot for ci in caja.instaladores],
        "total_items": len(caja.items),
    }
    db.delete(caja)
    db.commit()
    write_audit(db, action="caja_delete", actor=actor, entity_type="caja", entity_id=caja_id, details=snapshot)
    return None


# ── Plantillas de Caja ────────────────────────────────────────
def _plantilla_to_out(p: CajaPlantilla, h_by_id: dict[int, Herramienta]) -> PlantillaOut:
    items_out = [
        PlantillaItemOut(
            herramienta_id=it.herramienta_id,
            herramienta_nombre=(h_by_id.get(it.herramienta_id).nombre if h_by_id.get(it.herramienta_id) else ""),
            cantidad=int(it.cantidad or 0),
        )
        for it in p.items
    ]
    return PlantillaOut(id=p.id, nombre=p.nombre, items=items_out)


@router.get("/api/plantillas", response_model=list[PlantillaOut])
def list_plantillas(
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[PlantillaOut]:
    plantillas = db.query(CajaPlantilla).order_by(CajaPlantilla.nombre).all()
    h_by_id = {h.id: h for h in db.query(Herramienta).all()}
    return [_plantilla_to_out(p, h_by_id) for p in plantillas]


@router.post("/api/plantillas", response_model=PlantillaOut, status_code=status.HTTP_201_CREATED)
def create_plantilla(
    payload: PlantillaIn,
    actor: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> PlantillaOut:
    nombre = payload.nombre.strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="Nombre requerido")
    if db.query(CajaPlantilla).filter(CajaPlantilla.nombre == nombre).first() is not None:
        raise HTTPException(status_code=409, detail="Ya existe una plantilla con ese nombre")
    h_ids = [it.herramienta_id for it in payload.items]
    if len(h_ids) != len(set(h_ids)):
        raise HTTPException(status_code=400, detail="Herramientas duplicadas en la plantilla")
    h_rows = db.query(Herramienta).filter(Herramienta.id.in_(h_ids)).all()
    if len(h_rows) != len(h_ids):
        raise HTTPException(status_code=400, detail="Una o mas herramientas no existen")
    plantilla = CajaPlantilla(nombre=nombre)
    db.add(plantilla)
    db.flush()
    for it in payload.items:
        db.add(CajaPlantillaItem(plantilla_id=plantilla.id, herramienta_id=it.herramienta_id, cantidad=int(it.cantidad)))
    db.commit()
    db.refresh(plantilla)
    h_by_id = {h.id: h for h in h_rows}
    write_audit(
        db,
        action="plantilla_create",
        actor=actor,
        entity_type="plantilla",
        entity_id=plantilla.id,
        details={"nombre": plantilla.nombre, "items": [{"herramienta": h_by_id[it.herramienta_id].nombre, "cantidad": int(it.cantidad)} for it in payload.items]},
    )
    return _plantilla_to_out(plantilla, h_by_id)


@router.put("/api/plantillas/{plantilla_id}", response_model=PlantillaOut)
def update_plantilla(
    plantilla_id: int,
    payload: PlantillaIn,
    actor: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> PlantillaOut:
    plantilla = db.get(CajaPlantilla, plantilla_id)
    if plantilla is None:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    nombre = payload.nombre.strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="Nombre requerido")
    dupe = (
        db.query(CajaPlantilla)
        .filter(CajaPlantilla.nombre == nombre, CajaPlantilla.id != plantilla_id)
        .first()
    )
    if dupe is not None:
        raise HTTPException(status_code=409, detail="Ya existe otra plantilla con ese nombre")
    h_ids = [it.herramienta_id for it in payload.items]
    if len(h_ids) != len(set(h_ids)):
        raise HTTPException(status_code=400, detail="Herramientas duplicadas en la plantilla")
    h_rows = db.query(Herramienta).filter(Herramienta.id.in_(h_ids)).all()
    if len(h_rows) != len(h_ids):
        raise HTTPException(status_code=400, detail="Una o mas herramientas no existen")
    plantilla.nombre = nombre
    # Reemplaza items completamente.
    for it in list(plantilla.items):
        db.delete(it)
    db.flush()
    for it in payload.items:
        db.add(CajaPlantillaItem(plantilla_id=plantilla.id, herramienta_id=it.herramienta_id, cantidad=int(it.cantidad)))
    db.commit()
    db.refresh(plantilla)
    h_by_id = {h.id: h for h in h_rows}
    write_audit(
        db,
        action="plantilla_update",
        actor=actor,
        entity_type="plantilla",
        entity_id=plantilla.id,
        details={"nombre": plantilla.nombre, "items": [{"herramienta": h_by_id[it.herramienta_id].nombre, "cantidad": int(it.cantidad)} for it in payload.items]},
    )
    return _plantilla_to_out(plantilla, h_by_id)


@router.delete("/api/plantillas/{plantilla_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plantilla(
    plantilla_id: int,
    actor: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    plantilla = db.get(CajaPlantilla, plantilla_id)
    if plantilla is None:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    snapshot = {"nombre": plantilla.nombre, "item_count": len(plantilla.items)}
    db.delete(plantilla)
    db.commit()
    write_audit(db, action="plantilla_delete", actor=actor, entity_type="plantilla", entity_id=plantilla_id, details=snapshot)
    return None
