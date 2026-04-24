# 📦 Inventario — Control de Accesorios

Aplicación web para registrar el uso diario de accesorios (cables, conectores, herramientas, etc.) con roles de usuario (`admin` / `empleado`), historial, reportes en Excel y base de datos persistente.

Originalmente era un HTML con `localStorage` (cada navegador veía sus propios datos). Ahora todos los usuarios comparten el mismo inventario y registros a través de un backend con base de datos.

## 🌐 URLs de producción

- **App (frontend):** ver [`PROD_URLS.md`](./PROD_URLS.md)
- **API (backend):** ver [`PROD_URLS.md`](./PROD_URLS.md)

## 👤 Usuarios iniciales

| Usuario    | Contraseña | Rol        |
|------------|------------|------------|
| `admin`    | `admin123` | admin      |
| `empleado` | `emp123`   | empleado   |

> ⚠️ Cambia estas contraseñas cuanto antes desde la pestaña **USUARIOS** (crea un admin nuevo, cierra sesión, entra con el nuevo admin y elimina `admin`/`empleado` originales).

## 🧩 Arquitectura

```
┌────────────────────┐     HTTPS / JSON     ┌──────────────────────────┐
│ frontend/index.html│ ───────────────────▶ │ backend (FastAPI)        │
│ servido estático   │                      │ + SQLite en volumen Fly  │
│ en devinapps.com   │ ◀─────────────────── │ /data/inventario.db      │
└────────────────────┘                      └──────────────────────────┘
```

- **Frontend:** HTML/CSS/JS puro (sin build step). Toda la UI y los reportes Excel se generan en el navegador.
- **Backend:** FastAPI + SQLAlchemy + JWT. Endpoints bajo `/api/*`.
- **Base de datos:** SQLite sobre un volumen persistente en Fly.io. Apto para equipos pequeños/medianos. Puede migrarse a PostgreSQL cambiando `DATABASE_URL` (la capa de SQLAlchemy es compatible).

## 🔌 Endpoints principales

| Método | Ruta                        | Rol        | Descripción                                 |
|--------|-----------------------------|------------|---------------------------------------------|
| POST   | `/api/auth/login`           | público    | Login → devuelve JWT                         |
| GET    | `/api/auth/me`              | auth       | Usuario actual                               |
| GET    | `/api/inventory`            | auth       | Listar accesorios                            |
| POST   | `/api/inventory`            | admin      | Crear accesorio                              |
| PUT    | `/api/inventory/{id}`       | admin      | Editar accesorio                             |
| DELETE | `/api/inventory/{id}`       | admin      | Eliminar accesorio                           |
| GET    | `/api/usage`                | auth       | Listar registros de uso                      |
| POST   | `/api/usage`                | auth       | Registrar uso del día                        |
| DELETE | `/api/usage/{id}`           | admin      | Eliminar registro                            |
| GET    | `/api/users`                | admin      | Listar usuarios                              |
| POST   | `/api/users`                | admin      | Crear usuario                                |
| DELETE | `/api/users/{id}`           | admin      | Eliminar usuario (no puede eliminarse solo) |

## 💻 Desarrollo local

### Backend
```bash
cd backend
uv venv && source .venv/bin/activate
uv pip install -e .
uvicorn app.main:app --reload --port 8000
```

El backend creará automáticamente `inventario.db` (SQLite) en el directorio actual y sembrará los usuarios iniciales si la tabla está vacía.

### Frontend
```bash
cd frontend
python3 -m http.server 8080
# Abrir: http://localhost:8080/?api=http://localhost:8000
```

El parámetro `?api=...` le dice al frontend a qué backend apuntar. En producción esto ya viene configurado en el `<meta name="api-base">` del HTML.

## 🛠️ Configuración por variables de entorno

| Variable        | Default                                    | Descripción                                              |
|-----------------|--------------------------------------------|----------------------------------------------------------|
| `DATABASE_URL`  | `sqlite:///./inventario.db` (o `/data/...`) | Conexión a DB. Acepta `postgresql://...` también.       |
| `JWT_SECRET`    | generado y guardado en `/data/jwt_secret`  | Secreto para firmar tokens JWT.                          |
| `CORS_ORIGINS`  | `*`                                        | Lista separada por comas de orígenes permitidos.         |

## 📄 Licencia

MIT.
