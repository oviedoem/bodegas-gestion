# AGENTS.md — BODEGAS GESTION (ex Isabel Riquelme)

## Alcance
Cualquier agente que trabaje aquí debe limitarse a `E:\BODEGAS GESTION\`. Otros proyectos
(`E:\ferreteria-oviedo`, `W:\...`) son **solo lectura** — sirven de referencia de patrones
SQL/HTML, nunca se editan.

## Skill: safe-change / revisar-cambio (ahorro de tokens)
Ver `.claude/skills/safe-change/SKILL.md` y `.claude/skills/revisar-cambio/SKILL.md`
(checklist antes de cerrar cualquier cambio). Resumen del flujo vigente (10-09-2026,
reemplaza cualquier mención anterior a `generar_bodegas_ir.py`/`generar_bodegas_gestion.py`
— esos dos quedaron **archivados** en `_ARCHIVO_HISTORICO/` desde el 31-08-2026):
1. Leer `IDS_REFERENCIA_IR.md` / `IDS_REFERENCIA_BODEGAS_GESTION.md` — ya contienen
   IDBODEGA/IDSUCURSAL/columnas verificadas. No volver a explorar
   `INFORMATION_SCHEMA.COLUMNS` si el dato ya está documentado ahí.
2. Scripts vigentes (usar `ACTUALIZAR_DATOS.bat` para correr los 6 en orden, o a mano):
   - `generar_merma_ir.py` — Merma IR (bodega MIR=75) → `merma_isabel_riquelme.json` +
     **DOS** HTML (`index.html` es el panel real con login; `MERMA_ISABEL_RIQUELME.html`
     es un alias completo del mismo panel que se mantiene por compatibilidad con la URL
     vieja del repo `merma-isabel-riquelme`, ver `README.md`). **Cualquier cambio al
     render/tabla de `index.html` debe replicarse a mano en el `HTML_TEMPLATE` embebido
     en este script** — son dos copias del mismo JS, no hay forma de compartir código
     entre un HTML estático y un template Python sin refactor grande.
   - `scripts/descargar_bodegas_sql.py` — El Manzano/San Vicente/Las Cabras/Litueche/
     Compartidas + Otras Bodegas IR → `bodegas_gestion.json` + `bodegas_ir_otras.json`.
   - `scripts/generar_bodegas_modo.py` — recorta `bodegas_gestion.json` (no baja nada
     nuevo del ERP) → `data/bodegas-sv.json` + `data/bodegas-lc.json` (datasets livianos
     para MODO_SV/MODO_LC). **Siempre después** del script anterior.
   - `scripts/descargar_dif_sv.py`, `scripts/descargar_stock_critico_lc.py`,
     `scripts/descargar_oc_pendientes_lc.py` — completan los 6 pasos.
3. Descargas SQL de varias bodegas: siempre en lotes pequeños, nunca todas en una sola
   pasada — evita timeouts/conflictos con la conexión compartida al ERP.
4. Toda descarga debe tener regla anti-retroceso (abortar si trae <50% de lo anterior) y
   verificación de consistencia (comparar total por bodega/sucursal contra el `total`
   declarado en el JSON).
5. UI: `index.html` usa un diccionario `VISTAS` en JS para manejar varias pestañas/bodegas
   con el mismo código (`render(v)` es una sola función compartida) — agregar una vista
   nueva, no duplicar funciones render/filtrar/export.
6. No generar archivos de prueba sueltos en la carpeta (usar el scratchpad de la sesión o
   `_tmp_test/` y borrarlo antes de cerrar); sobrescribir los JSON/HTML en cada regeneración.
7. Al unir `M_Documentos_Encabezado_Observacion` o `M_DOCUMENTOS_ENCABEZADO` por
   `IDDOCUMENTO+IDNUMERO`: SIEMPRE filtrar también por `IDSUCURSAL` del lado de
   `M_DOCUMENTOS_DETALLE` (`N.IDSUCURSAL`), nunca contra la sucursal del stock destino —
   ese folio se repite entre sucursales (bug real corregido 10-09-2026, ver `CLAUDE.md`).

## Reglas de seguridad
- Jamás escribir el password SQL en un archivo de esta carpeta (ni en script, ni en HTML).
  Siempre leer desde `E:\ferreteria-oviedo\credenciales_db.ini` (path, no valor).
- Si Windows Defender bloquea la ejecución de un script nuevo aquí, revisar exclusiones
  antes de reintentar (no desactivar Defender globalmente).
- No subir nada de esta carpeta a git/repos compartidos sin revisión explícita del usuario.

## Acceso al reporte público (Firebase — isabel-riquelme-merma)
- El HTML (GitHub Pages oviedoem/bodegas-gestion) exige login Firebase Auth.
- **Arquitectura de datos vigente (JSON plano desde V.35 / 27-08-2026 — el sistema
  AES-256/.enc descrito en versiones anteriores de este archivo fue ELIMINADO, los
  `.enc` y `_cifrar_y_subir_clave.py` quedaron archivados en `_ARCHIVO_HISTORICO/`):**
  - `merma` → Firestore colección `merma` (sin cambios)
  - `bodegas` / `bodegas_gestion` → JSON en texto plano (`bodegas_gestion.json`,
    `bodegas_ir_otras.json`), servidos directo desde GitHub Pages/Firebase Hosting,
    SÍ van al repo (ya no están en `.gitignore`)
  - `index.html` los carga con `fetch()` directo tras el login, sin descifrado
- Para actualizar datos: correr `ACTUALIZAR_DATOS.bat` (6 pasos) → `git add
  bodegas_gestion.json bodegas_ir_otras.json data/*.json merma_isabel_riquelme.json
  MERMA_ISABEL_RIQUELME.html && git commit && git push` → `firebase deploy --only
  hosting --project isabel-riquelme-merma` (o `DEPLOY_APP.bat`).
- `_service_account.json` sigue en `.gitignore` (solo local, ya no se usa para cifrar
  nada, queda por si se necesita para algún script de Firestore puntual).
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
