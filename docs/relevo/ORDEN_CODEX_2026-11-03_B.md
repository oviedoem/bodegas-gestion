# ORDEN CODEX B - BODEGAS GESTION (E:, cuenta Ferreteria). Verificado por Claude: orden A OK (solo archivos nuevos).
Reglas: antirretroceso; sin git add/commit/push, sin Firebase/deploy, sin ejecutar ACTUALIZAR_DATOS.bat ni descargar_*.py; no borrar; no escribir secretos/IPs/usuarios/PIN en ningun archivo ni respuesta. Respaldo antes de mover en E:\_ARCHIVO_FERRETERIA\bodegas-orden-antes_2026-11-03 con MANIFIESTO.

## B1 - SQL: diagnostico solo lectura (sin cambiar nada)
La prueba fue NO concluyente (DPAPI no descifro; el .ini agoto el timeout). Diagnosticar en este orden y reportar cada resultado en 1 linea:
(a) DPAPI solo descifra con el MISMO usuario de Windows y sin sandbox: ejecutar el descifrado desde un proceso normal del usuario actual (no sandbox); (b) prueba de red al host SQL (puerto 1433, solo conexion TCP, sin enviar datos) para ver si la VPN esta activa; (c) si conecta: SELECT 1 y COUNT(*) de P_BODEGAS. Si la VPN esta caida, informar "VPN caida" y NO insistir. Registrar resultado en docs\relevo\LISTO_B.txt (sin IP ni usuario).

## B2 - Orden de archivos (modelo: E:\SQL\scripts\ordenar_archivos.py + scripts\bat\ORDENAR_ARCHIVOS.bat: informe por defecto, APLICAR mueve, --revertir)
Crear scripts\ordenar_archivos.py y scripts\bat\ORDENAR_ARCHIVOS.bat (ASCII) adaptados a este proyecto. Mover a historico\2026-11-03-orden\ SOLO candidatos seguros: monitor_sv.log, __pycache__ (raiz y scripts), respaldos/copias viejas. ANTES de mover cada uno: grep de su nombre en TODO el proyecto (.bat, .py, .html, .js, .json, .md; no solo la columna del CSV); si hay referencia viva, NO mover. NO mover: index.html, sw.js, *.json de datos, firestore.rules, firebase.json, DEPLOY_APP.bat, ACTUALIZAR_DATOS.bat, generar_merma_ir.py, scripts\*.py vigentes, CLAUDE.md, AGENTS.md, README.md, pipeline-bodegas-gestion.html, MERMA.xlsx, _service_account.json, monitor_inventario_sv.py (si lo usa algun .bat o tarea). Ejecutar primero informe, luego APLICAR, luego verificar: py_compile de los 7 scripts del pipeline y que ACTUALIZAR_DATOS.bat siga referenciando solo rutas que existen (Test-Path). MANIFIESTO.md ruta original -> nueva con forma de revertir. scripts\bat\README.md (3 lineas).

## B3 - Documentacion
Actualizar (agregando, sin borrar): CLAUDE.md (seccion Historial: sesion 2026-11-03: inventario, orden, estado SQL/VPN, datos 19 y 20-10 sin commit, firestore.rules con cambio del 26-09 sin desplegar - decision del dueno), AGENTS.md, y pipeline-bodegas-gestion.html solo si cambia el flujo. Crear docs\CIERRE_2026-11-03.md con tabla item|estado|evidencia (HECHO-VERIFICADO / PROGRAMADO / DELEGADO / BLOQUEADO) y como revertir.

## B4 - Drive (cuenta alejandrog45, unidad G:; si G: no existe, abrir GoogleDriveFS.exe "C:\Program Files\Google\Drive File Stream\133.0.2.0\GoogleDriveFS.exe" y esperar)
Crear G:\Mi unidad\PROYECTO_BODEGAS_GESTION con: copia SANEADA de CLAUDE.md, AGENTS.md, docs\, pipeline-bodegas-gestion.html, IDS_REFERENCIA_*.md, inventario.csv/arbol.txt (reemplazar claves, telefonos, IPs, PIN por [REDACTADO]); NUNCA .env, credenciales, _service_account.json, JSON de datos con clientes. Crear INDICE.md e INVENTARIO.md propios. No tocar indices existentes de Drive. Verificar con dir que existen.

## Cierre
Crear docs\relevo\LISTO_B_2026-11-03.txt con 1 linea por bloque (B1..B4: estado+evidencia) y confirmacion de que no se hizo git/deploy/pipeline. Al terminar verificar git status: solo cambios esperados.
