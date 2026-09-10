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

## Scripts principales (vigentes desde V.73, 31-08-2026 — reemplazan a los `generar_bodegas_*.py`
## archivados en `_ARCHIVO_HISTORICO/`, no usar esos)
- `generar_merma_ir.py` — lee códigos de `MERMA.xlsx`, consulta SQL (bodega MIR=75) y
  genera `merma_isabel_riquelme.json` + el HTML publicado (`MERMA_ISABEL_RIQUELME.html`
  / `index.html`) — este script genera el HTML completo, con TODOS los tabs.
- `scripts/descargar_bodegas_sql.py` — bodegas de El Manzano/San Vicente/Las Cabras/
  Litueche + Compartidas (CD y afines) + "Otras Bodegas IR" en lotes pequeños →
  `bodegas_gestion.json` + `bodegas_ir_otras.json`.
- `scripts/generar_bodegas_modo.py` — recorta `bodegas_gestion.json` (ya descargado
  por el script anterior, no baja nada nuevo del ERP) para armar `data/bodegas-sv.json`
  y `data/bodegas-lc.json`, los datasets livianos que cargan los usuarios MODO_SV/MODO_LC
  al login. **Siempre correr después de `descargar_bodegas_sql.py`, nunca antes** — si se
  olvida este paso, SV/LC quedan viendo datos de la última vez que corrió (bug real
  detectado 10-09-2026: quedaron 12 días desactualizados porque este paso no estaba en
  el pipeline).
- `scripts/descargar_dif_sv.py` → `data/dif-bodegas-sv.json` (tab Dif. Bodegas SV).
- `scripts/descargar_stock_critico_lc.py` / `scripts/descargar_oc_pendientes_lc.py` →
  datos de Solicitud Stock LC.
- `scripts/descargar_consumo_interno.py` (nuevo 11-09-2026) → `data/consumo-interno.json`,
  tab **Consumo Interno**. Consulta `M_DOCUMENTOS_DETALLE WHERE IDDOCUMENTO=218` ("Guia
  de Consumo", simbolo GEI) sin filtrar por bodega — el consumo puede salir de cualquiera.
  **Agrupa por la sucursal PROPIA de la bodega (`P_BODEGAS.IDSUCURSAL`), nunca por el
  `IDSUCURSAL` que trae el documento** — se verificó que ese campo no es confiable para
  este tipo de documento (la misma bodega aparece grabada bajo hasta 4 sucursales
  distintas, probablemente por registro centralizado). Ver comentario largo al inicio
  del script para el detalle completo de esta decisión. **Folio real:**
  `M_DOCUMENTOS_ENCABEZADO.NUMERO` (fix 11-09-2026 — `M_DOCUMENTOS_DETALLE.NUMERO`
  siempre vale 0 para este documento, verificado con SQL en vivo).
- `verificar_bodegas_gestion.py` — consulta `P_BODEGAS` en vivo para re-verificar IDs
  si cambia el ERP (no descarga movimientos, solo lista bodegas por categoría).

Para regenerar todo tras actualizar `MERMA.xlsx` o los IDs de bodega, correr
`ACTUALIZAR_DATOS.bat` (orquesta los 7 pasos en el orden correcto) o a mano:
```
E:\python-portable\python.exe "E:\BODEGAS GESTION\generar_merma_ir.py"
E:\python-portable\python.exe "E:\BODEGAS GESTION\scripts\descargar_bodegas_sql.py"
E:\python-portable\python.exe "E:\BODEGAS GESTION\scripts\generar_bodegas_modo.py"
E:\python-portable\python.exe "E:\BODEGAS GESTION\scripts\descargar_dif_sv.py"
E:\python-portable\python.exe "E:\BODEGAS GESTION\scripts\descargar_stock_critico_lc.py"
E:\python-portable\python.exe "E:\BODEGAS GESTION\scripts\descargar_oc_pendientes_lc.py"
E:\python-portable\python.exe "E:\BODEGAS GESTION\scripts\descargar_consumo_interno.py"
```
Después de correr `generar_merma_ir.py` ya queda el HTML final leyendo
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

### 2026-09-10 — Fix folio Consumo Interno + rediseño del tab (V.86/SW v92)
- **Bug de datos corregido:** `descargar_consumo_interno.py` leía el folio de
  `M_DOCUMENTOS_DETALLE.NUMERO` (siempre 0 para este documento) en vez de
  `M_DOCUMENTOS_ENCABEZADO.NUMERO` (el real) — verificado con SQL en vivo
  comparando contra la vista "Guía de Consumo" del ERP. Datos regenerados:
  100% de 13.143 eventos con folio (antes 3.6%). Commit `c6a22c9`.
- Tab Consumo Interno rediseñado: KPIs con período/fecha del más consumido,
  tabla "Desglose por sucursal" (con primera/última fecha del rango filtrado
  y detalle expandible), gráfico con selector Mensual/Por sucursal, colores
  del gráfico corregidos (estaban pensados para tema oscuro).
- Excel de Consumo Interno migrado de SheetJS a **ExcelJS** — es el único de
  los 4 Excel del proyecto con color/bordes reales, porque SheetJS Community
  no soporta estilos de celda al escribir (verificado con prueba directa).
  3 hojas: ranking, resumen por sucursal, detalle agrupado colapsable.
- Nuevo botón de descarga HTML interactivo (buscador + expandible, archivo
  autocontenido).
- Verificación consistencia de datos: 5 líneas idénticas de un mismo código
  en un mismo documento (folio 1724, código 72744) confirmadas como reales
  contra `M_DOCUMENTOS_DETALLE` — no es bug, es como quedó cargada la guía
  en el ERP (5 líneas de 5 unidades en vez de 1 de 25).
- Pendiente: `MERMA_ISABEL_RIQUELME.html` sigue sin la pestaña Consumo
  Interno (solo está en `index.html`).

### 2026-09-05 — Datos frescos (V.78/SW v84)
- Corridos los 5 pasos de `ACTUALIZAR_DATOS.bat`: Merma IR, Bodegas SQL (todas las
  sucursales), Diferencias SV, Stock crítico LC, OC pendientes LC — sin warnings de
  anti-retroceso, sin sucursales en 0
- `bodegas_gestion.json`: 9.797 códigos · `bodegas_ir_otras.json`: 4.521 códigos ·
  `dif-bodegas-sv.json`: 4.426 productos (142 con diferencia) · `stock-critico-lc.json`:
  1.465 productos · `oc-pend-resumen-lc.json`: 406 códigos (258 OCs activas)
- Commit `ef38488` (hook auto-bump a V.78/SW v84), deploy Firebase confirmado
  ("Deploy complete") en `isabel-riquelme-merma.web.app`
- Commit `fdb1625` (mismo cierre de sesión): bump manual a **V.79/SW v85** — versión
  real vigente en `index.html`/`sw.js`, no quedó registrado como entrada propia hasta
  ahora (revisión 08-09-2026)

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
