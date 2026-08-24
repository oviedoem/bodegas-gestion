# CLAUDE.md — Proyecto BODEGAS GESTION (ex "Isabel Riquelme / MERMA")

Proyecto **independiente** de cualquier otro (El Manzano, Las Cabras, etc).
Carpeta única de trabajo: `E:\BODEGAS GESTION\`.

> ⏳ **Rename en curso:** carpeta local ya renombrada a `BODEGAS GESTION`. Repo GitHub
> (`merma-isabel-riquelme`) y URL pública siguen con el nombre viejo hasta que el
> usuario confirme el cambio (ver sección Publicación abajo) — no asumir que ya se hizo.

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

## Publicación y seguridad de acceso (Firebase — actualizado 2026-08-24)
- Repo: github.com/oviedoem/bodegas-gestion · URL: https://oviedoem.github.io/bodegas-gestion/
- Proyecto Firebase **propio e independiente**: `isabel-riquelme-merma`. NUNCA reusar
  Firestore/Auth de `ferreteria-oviedo`.
- Login domain: `oviedo.cl`. Usuarios activos (2026-08-24):
  - `rrojas@oviedo.cl` — admin (todas las vistas)
  - `saliaga@oviedo.cl` — MODO_SV: solo San Vicente
  - `spavez@oviedo.cl` — MODO_LC: solo Las Cabras + Solicitud Stock LC
  La cuenta `riquelme` ya no existe en Auth.
- **`merma`**: Firestore colección `merma` (sin cambios).
- **`bodegas` / `bodegas_gestion` — JSON cifrado AES-256 (desde V.10 / 2026-08-24):**
  Los datos viven como `bodegas_gestion.enc` y `bodegas_ir_otras.enc` en el repo (cifrados,
  indescifrables sin la clave). La clave AES-256 está en Firestore `bodegas_clave/actual`
  (1 lectura/sesión). Descifrado en browser con Web Crypto API. **Cuota: 1 escritura por
  actualización** (vs 14000 del esquema antiguo).
- Para actualizar datos de bodegas (cifradas):
  ```
  python scripts/descargar_bodegas_sql.py      # genera JSON locales
  python _cifrar_y_subir_clave.py              # cifra .enc + sube clave a Firestore (1 escritura)
  git add bodegas_gestion.enc bodegas_ir_otras.enc && git push
  ```
- Para actualizar datos de Solicitud Stock LC (públicos, sin cifrar):
  ```
  python scripts/descargar_stock_critico_lc.py    # R_STOCK_PRODUCTOS → stock-critico-lc.json
  python scripts/descargar_oc_pendientes_lc.py    # M_DOCUMENTOS_DETALLE → oc-pend-resumen-lc.json
  git add data/stock-critico-lc.json data/oc-pend-resumen-lc.json && git push
  ```
- `_cifrar_y_subir_clave.py` usa `_service_account.json` (cuenta de servicio Firebase,
  gitignored). Nunca subir el service account al repo.
- Los JSON planos (`bodegas_gestion.json`, `bodegas_ir_otras.json`) están en `.gitignore`
  — solo existen localmente como fuente para el script de cifrado.

## Seguridad
- Nunca dejar credenciales SQL, IPs ni tokens visibles en HTML/JSON/commits de esta carpeta.
- Revisar Windows Defender si bloquea pyodbc/scripts nuevos en esta carpeta.
- VPN ya activa para acceso a SQL Server 200.6.118.110.

## Ahorro de tokens
Ver skill `safe-change` en `AGENTS.md` — antes de re-explorar SQL desde cero, revisar
`IDS_REFERENCIA_IR.md` e `IDS_REFERENCIA_BODEGAS_GESTION.md` (IDs ya verificados) en
esta misma carpeta.
