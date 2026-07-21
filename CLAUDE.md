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

## Publicación y seguridad de acceso (Firebase — desde 2026-06-27)
- Repo público (nombre viejo, pendiente rename a `bodegas-gestion`):
  github.com/oviedoem/merma-isabel-riquelme · URL actual:
  https://oviedoem.github.io/merma-isabel-riquelme/
- Proyecto Firebase **propio e independiente**: `isabel-riquelme-merma` (se mantiene
  este nombre aunque el proyecto se llame BODEGAS GESTION — decisión explícita del
  usuario, no recrear el proyecto Firebase). NUNCA reusar el Firestore/Auth de
  `ferreteria-oviedo`.
- El HTML publicado **ya no embebe los datos crudos**. Tiene pantalla de login (Firebase
  Auth) y los datos se cargan SOLO después de iniciar sesión.
- Usuario de login: `riquelme` (mapeado internamente a
  `riquelme@isabel-riquelme-merma.local` para Firebase Auth). La clave es aleatoria,
  generada por script — vive SOLO en `E:\BODEGAS GESTION\_CREDENCIAL_LOGIN_NO_SUBIR.txt`
  (excluido de git, nunca en texto plano en ningún commit/chat/log).
- **`merma`**: colección Firestore normal (1 doc por registro, ~427 docs, chico).
- **`bodegas` / `bodegas_gestion` — TEMPORAL fetch estático (desde 2026-07-21):**
  Firestore agotó su cuota gratuita de escrituras (Spark plan, 20K/día) subiendo estas
  dos colecciones con el esquema antiguo (1 doc por código, ~14000 escrituras). Mientras
  no resetee/se decida otra cosa, el HTML lee `bodegas_ir_otras.json` y
  `bodegas_gestion.json` directo por `fetch()` (archivos publicados junto al HTML,
  mismo repo). Esto NO empeoró la seguridad real: esos JSON ya estaban públicos por un
  descuido de commits previos (quedaron trackeados en git desde antes). **Pendiente:**
  revertir a Firestore con esquema "chunked" (pocos docs grandes por sucursal en vez de
  uno por código) y agregar esos JSON a `.gitignore` para cerrar la exposición de una
  vez. Ver `generar_merma_ir.py` (comentario "TEMPORAL" en `cargarDatosFirestore`).
- Para subir datos nuevos a Firestore: recrear un script puntual (estilo
  `_subir_firestore_chunked.py`, ya borrado tras su uso) que haga login como `riquelme`
  leyendo la clave SOLO de ese `.txt` local, y escriba vía REST de Firestore. Nunca
  imprimir la clave ni el idToken en ningún log/chat.

## Seguridad
- Nunca dejar credenciales SQL, IPs ni tokens visibles en HTML/JSON/commits de esta carpeta.
- Revisar Windows Defender si bloquea pyodbc/scripts nuevos en esta carpeta.
- VPN ya activa para acceso a SQL Server 200.6.118.110.

## Ahorro de tokens
Ver skill `safe-change` en `AGENTS.md` — antes de re-explorar SQL desde cero, revisar
`IDS_REFERENCIA_IR.md` e `IDS_REFERENCIA_BODEGAS_GESTION.md` (IDs ya verificados) en
esta misma carpeta.
