# BODEGAS GESTION — Ferretería Oviedo (ex "Merma Isabel Riquelme")

Reporte de análisis de bodegas de gestión interna (Merma, Gestión, Recepción, Ingreso,
Tránsito, Calzada, Exhibición, Distribución) para **5 sucursales** — Isabel Riquelme,
El Manzano, San Vicente, Las Cabras, Litueche — más las bodegas compartidas de Centro
de Distribución. Generado desde SQL Server Foviedo (solo lectura), cruzado con
`MERMA.xlsx` para la bodega de merma de Isabel Riquelme.

🔗 **Reporte público (URL vieja, pendiente rename del repo):**
https://oviedoem.github.io/merma-isabel-riquelme/

## Contenido

**Scripts vigentes** (reemplazan a `generar_bodegas_ir.py`/`generar_bodegas_gestion.py`,
archivados en `_ARCHIVO_HISTORICO/` desde el 31-08-2026 — no usar esos). Orden exacto y
detalle en `CLAUDE.md`/`AGENTS.md`, o correr `ACTUALIZAR_DATOS.bat` (los 7 en orden):
- `generar_merma_ir.py` — genera el HTML final (todos los tabs) + datos de Merma IR
  (bodega MIR=75).
- `scripts/descargar_bodegas_sql.py` — El Manzano/San Vicente/Las Cabras/Litueche +
  Compartidas (CD) + Otras Bodegas IR.
- `scripts/generar_bodegas_modo.py` — recorta el JSON anterior (no baja nada nuevo del
  ERP) para los datasets livianos de MODO_SV/MODO_LC. Siempre después del paso anterior.
- `scripts/descargar_dif_sv.py` — diferencias Disponible vs Físico, San Vicente.
- `scripts/descargar_stock_critico_lc.py` / `scripts/descargar_oc_pendientes_lc.py` —
  Solicitud Stock Las Cabras.
- `scripts/descargar_consumo_interno.py` — Guía de Consumo (GEI/218), todas las
  sucursales + recortes SV/LC.
- `verificar_bodegas_gestion.py` — utilidad: re-verifica IDs de bodega contra el ERP en
  vivo (no descarga movimientos).
- `ACTUALIZAR_MERMA_IR.bat` — atajo para refrescar solo Merma IR rápido (no reemplaza a
  `ACTUALIZAR_DATOS.bat`).

**Datos y reporte:**
- `index.html` / `MERMA_ISABEL_RIQUELME.html` — reporte visual interactivo (9 tabs,
  filtros, KPIs, exportar Excel/HTML, enviar por correo). Son 2 copias del mismo panel
  (compatibilidad con la URL vieja del repo) — cualquier fix al render se replica a mano
  en el `HTML_TEMPLATE` de `generar_merma_ir.py`.
- `merma_isabel_riquelme.json`, `bodegas_gestion.json`, `bodegas_ir_otras.json`,
  `data/*.json` — datos generados por los scripts, servidos estáticos desde GitHub
  Pages/Firebase Hosting (ver `CLAUDE.md`, sección Publicación).
- `pipeline-bodegas-gestion.html` — documentación viva del flujo completo (scripts,
  archivos, versión actual).
- `flujo-stock-justime.html` — referencia de columnas de stock y tipos de documento ERP.

**Referencia y reglas:**
- `IDS_REFERENCIA_IR.md` / `IDS_REFERENCIA_BODEGAS_GESTION.md` — IDs SQL verificados
  por sucursal/bodega.
- `CLAUDE.md` / `AGENTS.md` — reglas técnicas del proyecto. `CRITERIO.md` — criterios de
  decisión/juicio (independiente de otros proyectos de Ferretería Oviedo, nunca mezclar
  carpetas/repos).

## Seguridad
Este repositorio **no contiene credenciales** de ningún tipo. Las credenciales de SQL Server
se leen en tiempo de ejecución desde `E:\ferreteria-oviedo\credenciales_db.ini` (fuera de este
repo) y nunca se escriben en los archivos generados.
