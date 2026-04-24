"""FastAPI app: CORS, tablas, seed, rutas."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import hash_password
from .config import settings
from .db import Base, SessionLocal, engine
from .models import User
from .routes import auth as auth_routes
from .routes import inventory as inventory_routes
from .routes import usage as usage_routes
from .routes import users as users_routes


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
    app = FastAPI(title="Inventario API", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    Base.metadata.create_all(bind=engine)
    _seed_default_users()

    app.include_router(auth_routes.router)
    app.include_router(users_routes.router)
    app.include_router(inventory_routes.router)
    app.include_router(usage_routes.router)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
