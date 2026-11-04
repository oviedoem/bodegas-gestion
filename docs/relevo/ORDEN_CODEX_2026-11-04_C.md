# ORDEN CODEX C - BODEGAS GESTION (E:). Solo documentacion; sin git, deploy ni pipeline.
TOCO: CLAUDE.md y AGENTS.md (agregar entrada al historial, sin borrar nada), docs\CIERRE_2026-11-03.md (agregar seccion 04-11), copia saneada en G:\Mi unidad\PROYECTO_BODEGAS_GESTION (CLAUDE.md, AGENTS.md, docs\). NO TOCO: codigo, JSON, index.html, firestore.rules, DEPLOY_APP.bat, git.
Respaldo previo de CLAUDE.md y AGENTS.md en E:\_ARCHIVO_FERRETERIA\bodegas-docs-antes_2026-11-04.
Contenido a anotar (hechos verificados por Claude, 04-11-2026):
- Pipeline 7/7 corrido desde el Centro de Control, log 2026-11-04_001746_ok.log. Bodegas 10266/4794 codigos; dif SV 4457 productos (59 con diferencia, 0 anomalias); stock critico LC 1465; OC LC 234 OCs/376 codigos; consumo interno 13624 eventos, 7 sucursales.
- Prueba SQL desde el sandbox de Codex fallo (DPAPI/TCP) pero el pipeline normal conecta: no hace falta VPN.
- Publicado: commit 494aca2 (V.97/SW v103), push a main, deploy hosting a isabel-riquelme-merma; web.app y GitHub Pages 200.
- Sin commit por decision del dueno: firestore.rules (fix de seguridad 26-09, sin desplegar) y DEPLOY_APP.bat; historico/ ignorada en hosting.
- Ordenar archivos: 0 movidos (referencias vivas), MANIFIESTO en historico\2026-11-03-orden\.
- Estado: BLOQUEADO pendiente de decision del dueno: desplegar firestore.rules.
Al terminar: crear docs\relevo\LISTO_C_2026-11-04.txt (1 linea por archivo editado + confirmacion de que no hubo git/deploy). Sin secretos/IPs/PIN.
