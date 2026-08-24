# AGENTS.md — BODEGAS GESTION (ex Isabel Riquelme)

## Alcance
Cualquier agente que trabaje aquí debe limitarse a `E:\BODEGAS GESTION\`. Otros proyectos
(`E:\ferreteria-oviedo`, `W:\...`) son **solo lectura** — sirven de referencia de patrones
SQL/HTML, nunca se editan.

## Skill: safe-change (ahorro de tokens)
Ver `.claude/skills/safe-change/SKILL.md` para el detalle completo. Resumen:
1. Leer `IDS_REFERENCIA_IR.md` — ya contiene IDBODEGA/IDSUCURSAL/columnas verificadas.
   No volver a explorar `INFORMATION_SCHEMA.COLUMNS` si el dato ya está documentado ahí.
2. Reusar `generar_merma_ir.py` / `generar_bodegas_ir.py` / `generar_bodegas_gestion.py`
   como base — modificar parámetros (lista de bodegas, filtros de fecha, tipos de
   documento) en vez de reescribir el script. `generar_merma_ir.py` es el que arma el
   HTML final (todos los tabs); los otros dos solo generan JSON de datos.
3. Descargas SQL de varias bodegas: siempre en lotes pequeños (2 a la vez, con pausa),
   nunca todas en una sola pasada — evita timeouts/conflictos (ver `LOTE_SIZE` en
   `generar_bodegas_ir.py`).
4. Toda descarga debe tener regla anti-retroceso (abortar si trae <50% de lo anterior) y
   verificación de consistencia (comparar total por bodega contra `COUNT(*)` SQL).
5. UI: el HTML usa un diccionario `VISTAS` en JS para manejar varias pestañas/bodegas con
   el mismo código — agregar una vista nueva, no duplicar funciones render/filtrar/export.
6. No generar archivos de prueba sueltos en la carpeta; sobrescribir los JSON/HTML en
   cada regeneración.

## Reglas de seguridad
- Jamás escribir el password SQL en un archivo de esta carpeta (ni en script, ni en HTML).
  Siempre leer desde `E:\ferreteria-oviedo\credenciales_db.ini` (path, no valor).
- Si Windows Defender bloquea la ejecución de un script nuevo aquí, revisar exclusiones
  antes de reintentar (no desactivar Defender globalmente).
- No subir nada de esta carpeta a git/repos compartidos sin revisión explícita del usuario.

## Acceso al reporte público (Firebase — isabel-riquelme-merma)
- El HTML (GitHub Pages oviedoem/bodegas-gestion) exige login Firebase Auth.
- **Arquitectura de datos (desde V.10 / 2026-08-24):**
  - `merma` → Firestore colección `merma` (sin cambios)
  - `bodegas` → JSON cifrado AES-256-CBC: `bodegas_gestion.enc` + `bodegas_ir_otras.enc`
    (en el repo, son indescifrables sin la clave)
  - La clave AES vive en Firestore `bodegas_clave/actual` (1 lectura por sesión tras login)
  - Descifrado en browser con Web Crypto API (`crypto.subtle.decrypt`)
  - **Cuota usada por actualización: 1 escritura** (vs 14000 esquema anterior)
- Para actualizar datos: correr `scripts/descargar_bodegas_sql.py` → luego
  `_cifrar_y_subir_clave.py` (usa `_service_account.json`) → `git add *.enc && git push`
- `_service_account.json` y `_cifrar_y_subir_clave.py` están en `.gitignore` (solo locales).
- Proyecto Firebase propio (`isabel-riquelme-merma`), reglas Firestore `auth != null`.
  Nunca mezclar con Firebase de `ferreteria-oviedo`.
- Usuarios activos en Firebase Auth (2026-08-24):
  - `rrojas@oviedo.cl` — admin, todas las vistas
  - `saliaga@oviedo.cl` — MODO_SV: solo San Vicente
  - `spavez@oviedo.cl` — MODO_LC: solo Las Cabras + Solicitud Stock LC
  Login domain: `oviedo.cl` (configurado en `LOGIN_DOMAIN` del HTML).
- Repo GitHub: `oviedoem/bodegas-gestion` — URL: https://oviedoem.github.io/bodegas-gestion/

## Scripts Solicitud Stock Las Cabras (desde V.12/V.14)
- `scripts/descargar_stock_critico_lc.py` — R_STOCK_PRODUCTOS bodegas SLC=33,PLC=34,CLC=35,GLC=37
  → `data/stock-critico-lc.json` (en repo, público, no cifrado)
- `scripts/descargar_oc_pendientes_lc.py` — M_DOCUMENTOS_DETALLE OCs vigentes bodegas LC
  → `data/oc-pendientes-lc.json` (local, gitignored) + `data/oc-pend-resumen-lc.json` (en repo)
- Ambos usan `.strip().upper()` en CODIGO_TECNICO (fix mismatch de claves)
- Para actualizar: correr ambos scripts → `git add data/stock-critico-lc.json data/oc-pend-resumen-lc.json && git push`

## Regla VISTAS dict (evitar bug crítico V.12)
- El dict `VISTAS` en index.html registra vistas estándar (bodegas con bodega+render loop).
- `solicitud_lc` está en VISTAS pero se excluye del loop estándar con `VISTAS_STD`:
  ```js
  var VISTAS_STD = Object.keys(VISTAS).filter(function(v){ return v !== 'solicitud_lc'; });
  ```
- Cualquier vista nueva que NO use `initVista`/`render` debe añadirse a este filtro.
