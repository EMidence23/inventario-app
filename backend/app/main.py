"""FastAPI app: CORS, tablas, seed, rutas."""
from __future__ import annotations

import random

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import inspect, text

from .auth import hash_password
from .config import settings
from .db import Base, SessionLocal, engine
from .models import InventoryItem, User
from .routes import auth as auth_routes
from .routes import cajas as cajas_routes
from .routes import inventory as inventory_routes
from .routes import usage as usage_routes
from .routes import users as users_routes


_EXPECTED_USAGE_COLUMNS = {
    "id",
    "user_id",
    "username_snapshot",
    "date",
    "ts",
    "items_json",
}


def _migrate_add_missing_columns() -> None:
    """Migracion minima idempotente: repara el schema cuando SQLAlchemy
    create_all no basta (no ALTERa tablas existentes).

    - Si usage_records esta corrupto/legacy, lo borra (no habia datos de
      produccion en ese momento) y deja que create_all lo rehaga.
    - Agrega columnas opcionales como cat en inventory_items.
    """
    inspector = inspect(engine)
    is_sqlite = settings.database_url.startswith("sqlite")
    # Rebuilds one-shot: si la tabla usage_records viene de una version
    # anterior (faltan columnas o las filas son ilegibles), la borramos
    # para que Base.metadata.create_all la rehaga en estado limpio.
    if "usage_records" in inspector.get_table_names():
        rebuild = False
        existing = {c["name"] for c in inspector.get_columns("usage_records")}
        if not _EXPECTED_USAGE_COLUMNS.issubset(existing):
            rebuild = True
        elif is_sqlite:
            # El check con typeof() es especifico de SQLite; en Postgres
            # confiamos en que los tipos de columna ya garantizan consistencia.
            try:
                with engine.connect() as conn:
                    rows = conn.execute(
                        text(
                            "SELECT COUNT(*) FROM usage_records "
                            "WHERE ts IS NULL OR typeof(ts) != 'text' "
                            "OR date IS NULL OR items_json IS NULL"
                        )
                    ).scalar_one()
                if rows:
                    rebuild = True
            except Exception:
                rebuild = True
        if rebuild:
            with engine.begin() as conn:
                conn.execute(text("DROP TABLE IF EXISTS usage_records"))
            Base.metadata.create_all(bind=engine)
    if "inventory_items" in inspector.get_table_names():
        existing = {c["name"] for c in inspector.get_columns("inventory_items")}
        with engine.begin() as conn:
            if "cat" not in existing:
                conn.execute(text("ALTER TABLE inventory_items ADD COLUMN cat VARCHAR(80) DEFAULT ''"))
            if "stock" not in existing:
                # Nuevo campo de stock: lo agregamos y sembramos 100 en los
                # productos existentes para que el inventario arranque con un
                # valor razonable (el admin puede ajustarlo despues).
                conn.execute(text("ALTER TABLE inventory_items ADD COLUMN stock INTEGER NOT NULL DEFAULT 0"))
                conn.execute(text("UPDATE inventory_items SET stock = 100 WHERE stock = 0"))
            if "cost" not in existing:
                # Nuevo campo de costo unitario en lempiras. Sembramos un
                # costo aleatorio en cada producto existente solo como
                # placeholder; el admin lo reemplaza con los valores reales.
                conn.execute(
                    text(
                        "ALTER TABLE inventory_items "
                        "ADD COLUMN cost DOUBLE PRECISION NOT NULL DEFAULT 0"
                        if not is_sqlite
                        else "ALTER TABLE inventory_items ADD COLUMN cost REAL NOT NULL DEFAULT 0"
                    )
                )


def _seed_random_costs() -> None:
    """Asigna un costo aleatorio inicial (placeholder) a productos cuyo
    costo siga en 0.

    Se usa una semilla derivada del id del producto para que el mismo item
    siempre reciba el mismo numero pseudo-aleatorio en sucesivos arranques
    (idempotente). El admin puede sobrescribirlo desde la UI; al editar el
    valor real, este seed deja de tocarlo (solo afecta filas con cost=0).
    """
    with SessionLocal() as db:
        rows = db.query(InventoryItem).filter(InventoryItem.cost == 0).all()
        if not rows:
            return
        for item in rows:
            rng = random.Random(f"vimeco-cost-seed-{item.id}-{item.code}")
            item.cost = round(rng.uniform(5.0, 1500.0), 2)
        db.commit()


def _seed_default_users() -> None:
    """Crea los usuarios iniciales si la tabla de usuarios esta vacia."""
    with SessionLocal() as db:
        if db.query(User).count() > 0:
            return
        db.add_all(
            [
                User(
                    username="admin",
                    password_hash=hash_password("admin123"),
                    role="admin",
                ),
                User(
                    username="empleado",
                    password_hash=hash_password("emp123"),
                    role="empleado",
                ),
            ]
        )
        db.commit()


def create_app() -> FastAPI:
    app = FastAPI(title="Inventario API", version="1.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    Base.metadata.create_all(bind=engine)
    _migrate_add_missing_columns()
    _seed_default_users()
    _seed_random_costs()

    app.include_router(auth_routes.router)
    app.include_router(users_routes.router)
    app.include_router(inventory_routes.router)
    app.include_router(usage_routes.router)
    app.include_router(cajas_routes.router)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
