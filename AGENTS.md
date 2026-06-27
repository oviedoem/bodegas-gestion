# AGENTS.md — Isabel Riquelme

## Alcance
Cualquier agente que trabaje aquí debe limitarse a `E:\ISABEL RIQUELME\`. Otros proyectos
(`E:\ferreteria-oviedo`, `W:\...`) son **solo lectura** — sirven de referencia de patrones
SQL/HTML, nunca se editan.

## Skill: safe-change (ahorro de tokens)
Antes de cualquier tarea nueva en este proyecto:
1. Leer `IDS_REFERENCIA_IR.md` — ya contiene IDBODEGA/IDSUCURSAL/columnas verificadas.
   No volver a explorar `INFORMATION_SCHEMA.COLUMNS` si el dato ya está documentado ahí.
2. Reusar `generar_merma_ir.py` como base — modificar parámetros (lista de bodegas, filtros
   de fecha, tipos de documento) en vez de reescribir el script completo.
3. Conexión SQL: una sola consulta con `WHERE CODIGO_TECNICO IN (...)` para todos los
   códigos de una vez (ya implementado) — evitar loops de una consulta por código.
4. No generar archivos de prueba sueltos en la carpeta; sobrescribir
   `merma_isabel_riquelme.json` / `MERMA_ISABEL_RIQUELME.html` en cada regeneración.

## Reglas de seguridad
- Jamás escribir el password SQL en un archivo de esta carpeta (ni en script, ni en HTML).
  Siempre leer desde `E:\ferreteria-oviedo\credenciales_db.ini` (path, no valor).
- Si Windows Defender bloquea la ejecución de un script nuevo aquí, revisar exclusiones
  antes de reintentar (no desactivar Defender globalmente).
- No subir nada de esta carpeta a git/repos compartidos sin revisión explícita del usuario.
