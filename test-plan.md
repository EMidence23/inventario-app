# Test Plan — VIMECO, admin self-edit, hour in Uso Reciente, Reportes oculto

**App:** https://frontend-mmahpuvv.devinapps.com
**API:** https://inventario-backend-nkpdbvdn.fly.dev

## What changed (user-visible)
1. Branding VIMECO: title says "Control de Inventario VIMECO", logo VIMECO en login y header
2. Admin puede editar su propio usuario y contraseña desde USUARIOS → ✏️
3. La sección "Uso Reciente" del Dashboard muestra la hora del registro
4. Empleados no ven la pestaña Reportes (ni Usuarios); solo Inicio, Inventario, Registrar, Historial
5. Bug fixes: no hay loop de 401 tras logout; `todayStr` usa fecha local (no UTC)

## Code refs
- Logo login: `frontend/index.html:156`
- Logo + título en header: `frontend/index.html:178-184`
- Hora en Uso Reciente: `frontend/index.html:510,519` (`formatTime(u.ts)`)
- Reportes oculto por default: `frontend/index.html:293`
- Reportes activado solo para admin: `frontend/index.html:441`
- Botón ✏️ por usuario: `frontend/index.html:923`
- `openEditUserModal`: `frontend/index.html:938`
- `saveUser` con PUT: `frontend/index.html:950-979`
- Endpoint `PUT /api/users/{id}`: `backend/app/routes/users.py:49-87`
- doLogout sin switchTab: `frontend/index.html:421-434`
- `todayStr` local: `frontend/index.html:1004`

---

## Test 1 — Branding VIMECO
1. Abrir https://frontend-mmahpuvv.devinapps.com
   - **Pass:** La pestaña del navegador dice `Control de Inventario VIMECO`
   - **Pass:** En el login, aparece el logo VIMECO (imagen de ventana azul con fondo blanco) sobre el texto "VIMECO" y subtítulo "Control de Inventario · Ventanas y Puertas"
   - **Fail (si está roto):** Si hubiera un emoji 📦 en vez del logo, el título siguiera siendo "Control de Inventario" sin VIMECO, o la imagen no cargara (icono roto)

## Test 2 — Login + header + tabs como admin
2. Login con `admin` / `admin123`
   - **Pass:** Header superior muestra el mini-logo VIMECO + el texto "Control de Inventario VIMECO"
   - **Pass:** Bottom nav muestra 6 pestañas: INICIO, INVENTARIO, REGISTRAR, HISTORIAL, REPORTES, USUARIOS
   - **Fail:** Si el header dijera "📦 INVENTARIO" o faltara alguna pestaña

## Test 3 — Hora visible en Uso Reciente (y `todayStr` local correcto)
3. Ir a INVENTARIO → Agregar Accesorio → Código `VIM-001`, Nombre `Marco de ventana 1.20m`, Categoría `Ventanas` → Guardar
4. Ir a REGISTRAR → poner cantidad `3` en el accesorio `VIM-001` → GUARDAR USO
5. Volver a INICIO
   - **Pass:** En "Uso Reciente", la primera tarjeta muestra `📅 <fecha de hoy en formato DD/MM/YYYY> · 🕐 HH:MM por admin`, donde HH:MM coincide (±1 min) con la hora real del reloj local
   - **Pass:** El stat "Unidades Usadas Hoy" muestra `3` y "Registros de Hoy" muestra `1`
   - **Fail:** Si la tarjeta solo mostrara la fecha sin hora, o mostrara `--:--`, o si "Unidades Usadas Hoy" fuera `0` (lo que indicaría bug de `todayStr` UTC no clasificando el registro como "hoy")

## Test 4 — Admin edita su propio usuario y contraseña
6. Ir a USUARIOS → tocar ✏️ en la fila `admin` (tiene chip "Tú")
   - **Pass:** Modal abre con título "Editar mi cuenta", campo Usuario prellenado con `admin`, campo Contraseña vacío con texto ayuda "Déjalo vacío para mantener la contraseña actual", rol `Administrador`
7. Cambiar Usuario a `admin_vimeco`, Contraseña a `vimeco2026` → Guardar
   - **Pass:** Toast verde "✅ Usuario actualizado" aparece y la lista muestra la fila actualizada con `admin_vimeco`
8. Hacer logout (⏏️ arriba derecha)
9. Intentar login con credenciales viejas `admin` / `admin123`
   - **Pass:** Aparece error rojo `⚠️ Usuario o contraseña incorrectos` debajo del botón INGRESAR, NO entra a la app
   - **Fail:** Si entra con las credenciales viejas (backend no guardó el cambio)
10. Login con las nuevas `admin_vimeco` / `vimeco2026`
    - **Pass:** Entra al dashboard y el chip del header dice `👑 Admin`
    - **Fail:** Si el login falla con las nuevas credenciales
11. Revertir desde USUARIOS → ✏️ `admin_vimeco` → renombrar a `admin` y contraseña `admin123` → Guardar, para dejar la app en estado original (cleanup)

## Test 5 — Empleado no ve Reportes
12. Hacer logout y login con `empleado` / `emp123`
    - **Pass:** Bottom nav muestra solo 4 pestañas: INICIO, INVENTARIO, REGISTRAR, HISTORIAL (NO aparece REPORTES ni USUARIOS)
    - **Pass:** El chip de rol dice `👤 Empleado`
    - **Pass:** El accesorio `VIM-001` creado por admin aparece en INVENTARIO (prueba DB compartida)
    - **Fail:** Si aparece la pestaña REPORTES o USUARIOS en la barra inferior
13. Tocar ✏️ en la fila del empleado en... (N/A — no hay tab Usuarios) → saltar

## Regression — Logout no causa loop de 401
14. Durante el logout del Test 4 paso 8 y Test 5 paso 12, observar (no abrir DevTools, pero sí confirmar que):
    - **Pass:** No aparece ningún toast rojo "Sesión expirada" repitiéndose ni spinner infinito; la pantalla transiciona limpiamente al login
    - **Fail:** Si aparece una avalancha de toasts rojos o la pantalla queda congelada con el spinner
