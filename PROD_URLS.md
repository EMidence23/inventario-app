# 🌐 URLs de producción

| Pieza                  | URL                                                         |
|------------------------|-------------------------------------------------------------|
| App (frontend)         | https://frontend-deploy-ijnxzavl.devinapps.com              |
| API (backend)          | https://inventario-backend-nkpdbvdn.fly.dev                 |
| Documentación API      | https://inventario-backend-nkpdbvdn.fly.dev/docs            |
| Healthcheck            | https://inventario-backend-nkpdbvdn.fly.dev/api/health      |

## Usuarios iniciales sembrados automáticamente

| Usuario    | Contraseña  | Rol        |
|------------|-------------|------------|
| `admin`    | `admin123`  | admin      |
| `empleado` | `emp123`    | empleado   |

## Persistencia

- La base de datos SQLite vive en `/data/inventario.db` dentro del volumen persistente de Fly.io.
- El secreto JWT se genera en el primer arranque y se guarda en `/data/jwt_secret`.
- Ambos sobreviven reinicios, redeploys y escalamientos del servicio.
