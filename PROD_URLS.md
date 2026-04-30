# 🌐 URLs de producción

| Pieza                  | URL                                                         |
|------------------------|-------------------------------------------------------------|
| App (frontend)         | https://frontend-mmahpuvv.devinapps.com                     |
| API (backend)          | https://inventario-backend-nkpdbvdn.fly.dev                 |
| Documentación API      | https://inventario-backend-nkpdbvdn.fly.dev/docs            |
| Healthcheck            | https://inventario-backend-nkpdbvdn.fly.dev/api/health      |

## Usuario inicial sembrado automáticamente

| Usuario | Contraseña | Rol   |
|---------|------------|-------|
| `admin` | `admin123` | admin |

## Persistencia

- La base de datos SQLite vive en `/data/inventario.db` dentro del volumen persistente de Fly.io.
- El secreto JWT se genera en el primer arranque y se guarda en `/data/jwt_secret`.
- Ambos sobreviven reinicios, redeploys y escalamientos del servicio.
