# BODEGAS GESTION — Ferretería Oviedo (ex "Merma Isabel Riquelme")

Reporte de análisis de bodegas de gestión interna (Merma, Gestión, Recepción, Ingreso,
Tránsito, Calzada, Exhibición, Distribución) para **5 sucursales** — Isabel Riquelme,
El Manzano, San Vicente, Las Cabras, Litueche — más las bodegas compartidas de Centro
de Distribución. Generado desde SQL Server Foviedo (solo lectura), cruzado con
`MERMA.xlsx` para la bodega de merma de Isabel Riquelme.

🔗 **Reporte público (URL vieja, pendiente rename del repo):**
https://oviedoem.github.io/merma-isabel-riquelme/

## Contenido
- `index.html` / `MERMA_ISABEL_RIQUELME.html` — reporte visual interactivo (7 tabs,
  filtros, KPIs, exportar Excel/HTML, enviar por correo).
- `merma_isabel_riquelme.json` / `bodegas_ir_otras.json` / `bodegas_gestion.json` —
  datos generados por los scripts (los dos últimos se sirven estáticos por el HTML
  mientras Firestore no tenga cuota disponible, ver `CLAUDE.md`).
- `generar_merma_ir.py` — genera el HTML final (todos los tabs) + datos de Merma IR.
- `generar_bodegas_ir.py` — datos de "Otras Bodegas IR".
- `generar_bodegas_gestion.py` — datos de El Manzano/San Vicente/Las Cabras/Litueche +
  bodegas compartidas de Centro de Distribución.
- `verificar_bodegas_gestion.py` — re-verifica IDs de bodega contra el ERP en vivo.
- `ACTUALIZAR_MERMA_IR.bat` — corre `generar_merma_ir.py` y abre el reporte.
- `IDS_REFERENCIA_IR.md` / `IDS_REFERENCIA_BODEGAS_GESTION.md` — IDs SQL verificados
  por sucursal/bodega.
- `CLAUDE.md` / `AGENTS.md` — reglas del proyecto (independiente de otros proyectos de
  Ferretería Oviedo, nunca mezclar carpetas/repos).

## Seguridad
Este repositorio **no contiene credenciales** de ningún tipo. Las credenciales de SQL Server
se leen en tiempo de ejecución desde `E:\ferreteria-oviedo\credenciales_db.ini` (fuera de este
repo) y nunca se escriben en los archivos generados.
