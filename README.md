# Merma — Sucursal Isabel Riquelme (Ferretería Oviedo)

Reporte de análisis de merma de la sucursal **Isabel Riquelme** (bodega MIR), generado desde
SQL Server Foviedo (solo lectura) cruzado con `MERMA.xlsx`.

🔗 **Reporte público:** https://oviedoem.github.io/merma-isabel-riquelme/

## Contenido
- `index.html` / `MERMA_ISABEL_RIQUELME.html` — reporte visual interactivo (filtros, KPIs,
  exportar Excel/HTML, enviar por correo).
- `merma_isabel_riquelme.json` — datos crudos del reporte.
- `generar_merma_ir.py` — script que descarga desde SQL Server (solo lectura) y regenera el reporte.
- `ACTUALIZAR_MERMA_IR.bat` — actualiza datos y vuelve a abrir el reporte.
- `IDS_REFERENCIA_IR.md` — IDs SQL verificados (sucursal, bodega, columnas).
- `CLAUDE.md` / `AGENTS.md` — reglas del proyecto (independiente de otros proyectos de
  Ferretería Oviedo, nunca mezclar carpetas/repos).

## Seguridad
Este repositorio **no contiene credenciales** de ningún tipo. Las credenciales de SQL Server
se leen en tiempo de ejecución desde `E:\ferreteria-oviedo\credenciales_db.ini` (fuera de este
repo) y nunca se escriben en los archivos generados.
