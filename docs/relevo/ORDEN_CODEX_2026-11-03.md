# ORDEN CODEX 2026-11-03 - BODEGAS GESTION (E:, cuenta Ferreteria)
TOCO: solo crear archivos nuevos en `E:\BODEGAS GESTION\historico\inventario_2026-11-03\` y `scripts\bat\` (INVENTARIO_RUTAS.bat). 
NO TOCO: ningun archivo existente, JSON de datos, index.html, sw.js, firestore.rules, DEPLOY_APP.bat, ACTUALIZAR_DATOS.bat, git (sin add/commit/push), Firebase (sin deploy), Drive. No mover ni borrar nada. No ejecutar ACTUALIZAR_DATOS.bat ni ningun descargar_*.py.
Python: E:\python-portable\python.exe. No escribir secretos/IPs/usuarios en ningun archivo ni en la respuesta.

## Tarea 1 - Prueba SQL de SOLO LECTURA
Usar la logica de lectura de credenciales de `scripts\descargar_bodegas_sql.py` (E:\config\credenciales_db.enc, DPAPI) en un script temporal fuera del proyecto (scratchpad). Ejecutar solo `SELECT 1` y `SELECT COUNT(*) FROM P_BODEGAS`. Informar: conecta SI/NO y el conteo. Nada mas.

## Tarea 2 - Inventario (modelo: W:\PROYECTOS CUENTA ALEJANDROG45\INVENTARIO_RUTAS_W.bat, termina con pause)
Crear `scripts\bat\INVENTARIO_RUTAS.bat` (solo ASCII) que genere en `historico\inventario_2026-11-03\`: inventario.csv (ruta, tamano, fecha, extension, referenciado_por via grep de nombre en TODO el proyecto excluyendo historico y .git), arbol.txt y resumen.log. Marcar candidatos a mover (logs, __pycache__, monitor_sv.log, respaldos) SIN mover. Ejecutarlo una vez. Excluir _service_account.json del contenido (solo listar nombre).

## Tarea 3 - Cierre
Crear `historico\inventario_2026-11-03\README.md` (3 lineas) y, al terminar, `docs\relevo\LISTO_2026-11-03.txt` con: resultado SQL (SI/NO + conteo), cantidad de archivos inventariados, candidatos a mover, y confirmacion de que no se toco nada mas. Verificar con `git status --short` que solo aparecen archivos nuevos en esas rutas.
