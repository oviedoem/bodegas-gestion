# CLAUDE.md — Proyecto BODEGAS GESTION (ex "Isabel Riquelme / MERMA")

Proyecto **independiente** de cualquier otro (El Manzano, Las Cabras, etc).
Carpeta única de trabajo: `E:\BODEGAS GESTION\`.

> ⏳ **Rename en curso:** carpeta local ya renombrada a `BODEGAS GESTION`. Repo GitHub
> (`merma-isabel-riquelme`) y URL pública siguen con el nombre viejo hasta que el
> usuario confirme el cambio (ver sección Publicación abajo) — no asumir que ya se hizo.

## REGLA FLUJO ACTUAL — leer al inicio de cada sesión

Revisar fechas de modificación de archivos en la raíz. Los más recientes marcan el flujo actual:
```powershell
Get-ChildItem "E:\BODEGAS GESTION" -File | Sort-Object LastWriteTime -Descending | Select-Object Name, LastWriteTime | Select-Object -First 20
```
Un `.html`, `.py` o `.json` con fecha reciente puede indicar pipeline nuevo no documentado aún.

## Regla de oro — NUNCA EDITAR OTROS PROYECTOS
- Solo se puede LEER (revisar/copiar referencia) de otros proyectos: `E:\ferreteria-oviedo\`,
  `W:\` (Las Cabras), `E:\SQL\`, etc.
- Editar y guardar SOLO dentro de `E:\BODEGAS GESTION\`.
- Si algo de otro proyecto sirve de referencia, copiarlo a esta carpeta y adaptarlo aquí,
  jamás modificar el original.

## Alcance del proyecto (multi-sucursal desde 2026-07-21)
Empezó como reporte de Merma solo de Isabel Riquelme, se amplió a "BODEGAS GESTION":
bodegas de gestión interna (Gestión/Merma/Recepción/Ingreso/Tránsito/Calzada/
Exhibición/Distribución) de **5 sucursales** + bodegas compartidas de Centro de
Distribución:
- Isabel Riquelme (02) — bodega Merma **MIR**=75, más "Otras Bodegas IR".
- El Manzano (04), San Vicente (05), Las Cabras (06), Litueche (11).
- Compartidas (viven bajo otro IDSUCURSAL administrativo en el ERP): Centro de
  Distribución, CrossDock, Gestión/Ingreso/Merma/Recepción/Tránsito CD, Despacho
  Proveedor, Remate, Marketing.

IDs SQL verificados: ver `IDS_REFERENCIA_IR.md` (Isabel Riquelme) e
`IDS_REFERENCIA_BODEGAS_GESTION.md` (las otras 4 sucursales + compartidas).

## Scripts principales
- `generar_merma_ir.py` — lee códigos de `MERMA.xlsx`, consulta SQL (bodega MIR=75) y
  genera `merma_isabel_riquelme.json` + el HTML publicado (`MERMA_ISABEL_RIQUELME.html`
  / `index.html`) — este script genera el HTML completo, con TODOS los tabs (incluye
  los de `generar_bodegas_gestion.py`, ver abajo).
- `generar_bodegas_ir.py` — bodegas "Otras Bodegas IR" (CAL, SER, WEB, GO, GAR, IIR,
  BMC, RST, HEL, EIR) en lotes de 2 → `bodegas_ir_otras.json`.
- `generar_bodegas_gestion.py` — bodegas de El Manzano/San Vicente/Las Cabras/Litueche
  + Compartidas (CD y afines) en lotes de 2 → `bodegas_gestion.json`.
- `verificar_bodegas_gestion.py` — consulta `P_BODEGAS` en vivo para re-verificar IDs
  si cambia el ERP (no descarga movimientos, solo lista bodegas por categoría).

Para regenerar tras actualizar `MERMA.xlsx` o los IDs de bodega:
```
E:\python-portable\python.exe "E:\BODEGAS GESTION\generar_merma_ir.py"
E:\python-portable\python.exe "E:\BODEGAS GESTION\generar_bodegas_ir.py"
E:\python-portable\python.exe "E:\BODEGAS GESTION\generar_bodegas_gestion.py"
```
Después de correr los 3, `generar_merma_ir.py` ya generó el HTML final leyendo
`merma_isabel_riquelme.json` — no hace falta un paso aparte para "armar" el HTML.

## Publicación y seguridad de acceso (actualizado 2026-08-27 — V.35/SW v41)
- Repo: github.com/oviedoem/bodegas-gestion · URL: https://oviedoem.github.io/bodegas-gestion/
- Proyecto Firebase **propio e independiente**: `isabel-riquelme-merma`. NUNCA reusar
  Firestore/Auth de `ferreteria-oviedo`.
- Login domain: `oviedo.cl`. Usuarios activos:
  - `rrojas@oviedo.cl` — admin (todas las vistas)
  - `saliaga@oviedo.cl` — MODO_SV: solo San Vicente
  - `spavez@oviedo.cl` — MODO_LC: solo Las Cabras + Solicitud Stock LC
- **`merma`**: Firestore colección `merma` (sin cambios).
- **`bodegas` / `bodegas_gestion` — JSON en texto plano (desde 2026-08-27):**
  Los `.enc` (AES-256) fueron eliminados del flujo activo y movidos a `_ARCHIVO_HISTORICO/`.
  `index.html` fetchea `bodegas_gestion.json` y `bodegas_ir_otras.json` directamente desde
  GitHub Pages. Ambos archivos **SÍ van al repo** (ya no están en `.gitignore`).
- Para actualizar datos de bodegas:
  ```powershell
  python scripts/descargar_bodegas_sql.py      # genera JSON locales
  git add bodegas_gestion.json bodegas_ir_otras.json && git push
  E:\npm-global\firebase.cmd deploy --only hosting --project isabel-riquelme-merma
  ```
- Para actualizar datos de Solicitud Stock LC:
  ```powershell
  python scripts/descargar_stock_critico_lc.py    # R_STOCK_PRODUCTOS → stock-critico-lc.json
  python scripts/descargar_oc_pendientes_lc.py    # M_DOCUMENTOS_DETALLE → oc-pend-resumen-lc.json
  git add data/stock-critico-lc.json data/oc-pend-resumen-lc.json && git push
  ```
- `_service_account.json` — gitignoreado. Nunca subir al repo.
- **Archivos históricos eliminados del flujo activo** (en `_ARCHIVO_HISTORICO/`):
  `bodegas_gestion.enc`, `bodegas_ir_otras.enc`, `_cifrar_y_subir_clave.py`,
  `_subir_firestore_chunked.py`, `DESCARGAR_BODEGAS.bat`, `datos-bodegas.xlsm`.

## Seguridad
- Nunca dejar credenciales SQL, IPs ni tokens visibles en HTML/JSON/commits de esta carpeta.
- Revisar Windows Defender si bloquea pyodbc/scripts nuevos en esta carpeta.
- VPN ya activa para acceso a SQL Server [SQL-SERVER-IP].

## Historial reciente

### 2026-08-27 — Migración cifrado→JSON plano (V.35/SW v41)
- **Eliminado sistema AES-256:** `.enc` + `_cifrar_y_subir_clave.py` movidos a `_ARCHIVO_HISTORICO/`
- `index.html` ahora fetchea `bodegas_gestion.json` y `bodegas_ir_otras.json` directamente desde GitHub Pages
- `bodegas_gestion.json` y `bodegas_ir_otras.json` removidos de `.gitignore` → ahora van al repo
- `pipeline-bodegas-gestion.html` agregado — documentación viva del flujo actual
- `.gitignore` actualizado (27-08), `IDS_REFERENCIA_BODEGAS_GESTION.md` actualizado
- `merma_isabel_riquelme.json` y `MERMA_ISABEL_RIQUELME.html` actualizados

### 2026-08-28 — Investigación CSV + documentación de tipos de documento
- `INVESTIGACION_26129_CSV.md` — análisis stock código 26129 en Calzada San Vicente (IDBODEGA=44)
- `TIPOS_STOCK_DOCUMENTOS.md` — tabla de comportamiento de stock por tipo de documento ERP
- `flujo-stock-justime.html` actualizado (12:55)
- `index.html` y `sw.js` actualizados (17:44)

## Ahorro de tokens
Ver skill `safe-change` en `AGENTS.md` — antes de re-explorar SQL desde cero, revisar
`IDS_REFERENCIA_IR.md` e `IDS_REFERENCIA_BODEGAS_GESTION.md` (IDs ya verificados) en
esta misma carpeta.
