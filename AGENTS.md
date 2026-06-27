# AGENTS.md — Isabel Riquelme

## Alcance
Cualquier agente que trabaje aquí debe limitarse a `E:\ISABEL RIQUELME\`. Otros proyectos
(`E:\ferreteria-oviedo`, `W:\...`) son **solo lectura** — sirven de referencia de patrones
SQL/HTML, nunca se editan.

## Skill: safe-change (ahorro de tokens)
Ver `.claude/skills/safe-change/SKILL.md` para el detalle completo. Resumen:
1. Leer `IDS_REFERENCIA_IR.md` — ya contiene IDBODEGA/IDSUCURSAL/columnas verificadas.
   No volver a explorar `INFORMATION_SCHEMA.COLUMNS` si el dato ya está documentado ahí.
2. Reusar `generar_merma_ir.py` / `generar_bodegas_ir.py` como base — modificar parámetros
   (lista de bodegas, filtros de fecha, tipos de documento) en vez de reescribir el script.
3. Descargas SQL de varias bodegas: siempre en lotes pequeños (2 a la vez, con pausa),
   nunca todas en una sola pasada — evita timeouts/conflictos (ver `LOTE_SIZE` en
   `generar_bodegas_ir.py`).
4. Toda descarga debe tener regla anti-retroceso (abortar si trae <50% de lo anterior) y
   verificación de consistencia (comparar total por bodega contra `COUNT(*)` SQL).
5. UI: el HTML usa un diccionario `VISTAS` en JS para manejar varias pestañas/bodegas con
   el mismo código — agregar una vista nueva, no duplicar funciones render/filtrar/export.
6. No generar archivos de prueba sueltos en la carpeta; sobrescribir los JSON/HTML en
   cada regeneración.

## Reglas de seguridad
- Jamás escribir el password SQL en un archivo de esta carpeta (ni en script, ni en HTML).
  Siempre leer desde `E:\ferreteria-oviedo\credenciales_db.ini` (path, no valor).
- Si Windows Defender bloquea la ejecución de un script nuevo aquí, revisar exclusiones
  antes de reintentar (no desactivar Defender globalmente).
- No subir nada de esta carpeta a git/repos compartidos sin revisión explícita del usuario.

## Acceso al reporte público (Firebase — isabel-riquelme-merma)
- El HTML público (GitHub Pages) exige login (Firebase Auth) y carga datos desde
  Firestore — NUNCA volver a embeber datos crudos directamente en el HTML.
- Proyecto Firebase propio (`isabel-riquelme-merma`), reglas Firestore `auth != null`.
  Nunca mezclar con el proyecto Firebase de `ferreteria-oviedo`.
- Usuario de login `riquelme`; la clave vive SOLO en
  `_CREDENCIAL_LOGIN_NO_SUBIR.txt` (gitignored). Nunca teclear/imprimir esa clave en
  ningún comando, archivo o respuesta — ver sección 5-6 de `.claude/skills/safe-change/SKILL.md`.
