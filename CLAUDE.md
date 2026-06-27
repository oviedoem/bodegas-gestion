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

## Script principal
`generar_merma_ir.py` — lee códigos de `MERMA.xlsx`, consulta SQL (solo lectura) y genera:
- `merma_isabel_riquelme.json` (datos crudos)
- `MERMA_ISABEL_RIQUELME.html` (reporte visual, igual estructura que "Análisis de Bodegas"
  del panel admin de El Manzano: bodega, tipo doc, folio, código, descripción, disp, físico,
  costo, fecha registro, días antigüedad, valorizado, observación, **usuario** (IDRESPONZABLE/
  AUTORIZADO_FIRMA/IDVENDEDOR de `M_DOCUMENTOS_ENCABEZADO`) y **estación/PC** (`ESTACION`).

Para regenerar el reporte tras actualizar `MERMA.xlsx`:
```
E:\python-portable\python.exe "E:\ISABEL RIQUELME\generar_merma_ir.py"
```

## Seguridad
- Nunca dejar credenciales, IPs ni tokens visibles en HTML/JSON/commits de esta carpeta.
- Revisar Windows Defender si bloquea pyodbc/scripts nuevos en esta carpeta.
- VPN ya activa para acceso a SQL Server [SQL-SERVER-IP].

## Ahorro de tokens
Ver skill `safe-change` en `AGENTS.md` — antes de re-explorar SQL desde cero, revisar
`IDS_REFERENCIA_IR.md` (IDs ya verificados) en esta misma carpeta.
