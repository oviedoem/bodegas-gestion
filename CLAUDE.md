# CLAUDE.md — Proyecto Isabel Riquelme (MERMA)

Proyecto **independiente** de cualquier otro (El Manzano, Las Cabras, etc).
Carpeta única de trabajo: `E:\ISABEL RIQUELME\`.

## Regla de oro — NUNCA EDITAR OTROS PROYECTOS
- Solo se puede LEER (revisar/copiar referencia) de otros proyectos: `E:\ferreteria-oviedo\`,
  `W:\` (Las Cabras), etc.
- Editar y guardar SOLO dentro de `E:\ISABEL RIQUELME\`.
- Si algo de otro proyecto sirve de referencia, copiarlo a esta carpeta y adaptarlo aquí,
  jamás modificar el original.

## Datos del proyecto
- Sucursal: **Isabel Riquelme** → `IDSUCURSAL = '02'` en SQL Server Foviedo.
- Bodega de merma: **MIR** (Mermas Isabel Riquelme) → `IDBODEGA = 75`.
- Fuente de stock: `MERMA.xlsx` (export manual ERP) con columna `Codigo Producto`.
- Credenciales SQL: se leen en solo-lectura desde `E:\ferreteria-oviedo\credenciales_db.ini`
  (NUNCA copiar el password a archivos de esta carpeta, NUNCA mostrarlo en HTML/JSON).

## Scripts principales
- `generar_merma_ir.py` — lee códigos de `MERMA.xlsx`, consulta SQL (solo lectura, bodega
  MIR=75) y genera `merma_isabel_riquelme.json` + `MERMA_ISABEL_RIQUELME.html`/`index.html`.
- `generar_bodegas_ir.py` — igual pero para las otras 9 bodegas IR (CAL, SER, WEB, GO,
  GAR, IIR, BMC, RST, HEL) en lotes de 2, genera `bodegas_ir_otras.json`.

Para regenerar tras actualizar `MERMA.xlsx`:
```
E:\python-portable\python.exe "E:\ISABEL RIQUELME\generar_merma_ir.py"
E:\python-portable\python.exe "E:\ISABEL RIQUELME\generar_bodegas_ir.py"
```

## Publicación y seguridad de acceso (Firebase — desde 2026-06-27)
- Repo público: github.com/oviedoem/merma-isabel-riquelme · URL: https://oviedoem.github.io/merma-isabel-riquelme/
- Proyecto Firebase **propio e independiente**: `isabel-riquelme-merma` (NUNCA reusar el
  Firestore/Auth de `ferreteria-oviedo`).
- El HTML publicado **ya no embebe los datos crudos**. Tiene pantalla de login (Firebase
  Auth) y los datos (`merma`, `bodegas` collections) se cargan desde Firestore SOLO
  después de iniciar sesión — reglas (`firestore.rules`): `allow read, write: if
  request.auth != null`.
- Usuario de login: `riquelme` (mapeado internamente a
  `riquelme@isabel-riquelme-merma.local` para Firebase Auth). La clave es aleatoria,
  generada por script — vive SOLO en `E:\ISABEL RIQUELME\_CREDENCIAL_LOGIN_NO_SUBIR.txt`
  (excluido de git, nunca en texto plano en ningún commit/chat/log).
- Para subir datos nuevos a Firestore tras regenerar los JSON: recrear un script puntual
  (estilo `_subir_datos_firestore.py`, ya borrado tras su uso) que haga login como
  `riquelme` leyendo la clave SOLO de ese `.txt` local, y escriba vía REST de Firestore.
  Nunca imprimir la clave ni el idToken en ningún log/chat.

## Seguridad
- Nunca dejar credenciales SQL, IPs ni tokens visibles en HTML/JSON/commits de esta carpeta.
- Revisar Windows Defender si bloquea pyodbc/scripts nuevos en esta carpeta.
- VPN ya activa para acceso a SQL Server [SQL-SERVER-IP].

## Ahorro de tokens
Ver skill `safe-change` en `AGENTS.md` — antes de re-explorar SQL desde cero, revisar
`IDS_REFERENCIA_IR.md` (IDs ya verificados) en esta misma carpeta.
