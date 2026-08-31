---
name: safe-change
description: Reglas de cambio seguro, ahorro de tokens y no mezclar proyectos para BODEGAS GESTION. Activar antes de cualquier cambio en index.html, scripts Python o JSONs de datos.
---

# safe-change — BODEGAS GESTION (ex Isabel Riquelme)

Reglas obligatorias para cualquier cambio en este proyecto (`E:\BODEGAS GESTION\`).
Ver también: skill global `ahorro-tokens` en `C:\Users\alejandro\.claude\skills\ahorro-tokens\SKILL.md`.

## Estado actual del proyecto (2026-08-31)
- `index.html`: V.73 / SW v79 — inventario SV propagado, monitor ntfy, commit dc32666
- Usuarios Firebase: `rrojas` (admin), `saliaga` (MODO_SV), `spavez` (MODO_LC)
- **Datos en JSON plano** (desde 2026-08-27): `bodegas_gestion.json` y `bodegas_ir_otras.json`
  servidos directamente desde GitHub Pages. Los `.enc` AES-256 fueron eliminados del flujo activo.
- URL autoritativa: `isabel-riquelme-merma.web.app`
- Deploy: `git push` (GitHub Pages auto) + `firebase deploy --only hosting --project isabel-riquelme-merma`

## 1. No mezclar proyectos (REGLA ABSOLUTA)
- Solo se edita dentro de `E:\BODEGAS GESTION\`. Otros proyectos (`E:\ferreteria-oviedo`,
  `W:\SUCURSAL LAS CABRAS`, `E:\git-sync`) son **solo lectura** — copiar y adaptar aquí,
  nunca modificar el original.
- El repo GitHub de este proyecto (`oviedoem/bodegas-gestion`) es independiente del
  de El Manzano — nunca usar `E:\git-sync` para esto.
- Una tarea a la vez — completar y confirmar antes de la siguiente.

## 2. Ahorro de tokens — no re-explorar lo ya verificado
- IDs verificados en `IDS_REFERENCIA_IR.md` e `IDS_REFERENCIA_BODEGAS_GESTION.md`.
  No volver a correr `INFORMATION_SCHEMA.COLUMNS` si el dato ya está documentado.
- Comportamiento de stock/documentos: en `flujo-stock-justime.html` (sección Referencia ERP).
- Antes de escribir query SQL nueva, revisar scripts `.py` existentes — tienen el JOIN correcto.
- `index.html` supera 2000 líneas — usar `Grep` para ubicar secciones, luego `Read` con offset+limit.
- No leer `CLAUDE.md` / `AGENTS.md` si ya están en contexto de la sesión actual.

## 3. Descargas SQL — por lotes pequeños
- Nunca bajar todas las bodegas en una sola consulta masiva. `scripts/descargar_bodegas_sql.py`
  descarga por sucursal en lotes — seguir ese patrón si se agregan más bodegas, para evitar
  timeouts/conflictos en la conexión SQL compartida con el ERP.
- Verificar consistencia después de cada descarga: comparar `total códigos` por bodega
  contra un `COUNT(*)` directo en `R_STOCK_PRODUCTOS` antes de confiar en el resultado
  (ver bloque `RESUMEN / CONSISTENCIA POR BODEGA` que imprime el script).
- Si alguna sucursal sale en 0 tras una descarga: esperar 5-10 min y repetir (puede ser
  que el ERP esté procesando un inventario — lección aprendida 29-08-2026 con SV).

## 4. Regla anti-retroceso (obligatoria en todo script de descarga)
- Si la nueva descarga trae menos del 50% de los registros del JSON anterior, abortar
  el sobrescrito y conservar el archivo anterior. Ya implementado en
  `generar_merma_ir.py` y `scripts/descargar_bodegas_sql.py` — replicar este bloque en
  cualquier script de descarga nuevo.

## 5. Seguridad de credenciales
- Las credenciales SQL nunca se escriben en archivos de esta carpeta ni en el repo
  público. Se leen en tiempo de ejecución desde `E:\ferreteria-oviedo\credenciales_db.ini`
  (ruta, no valor).
- La clave de login del HTML (usuario `riquelme`) NUNCA se teclea literal en ningún
  comando/archivo que el asistente genere — se crea con clave aleatoria via script
  (`_setup_firebase_auth.py`) y se guarda solo en `_CREDENCIAL_LOGIN_NO_SUBIR.txt`
  (excluido en `.gitignore`, nunca se imprime en logs/chat).
- Antes de cualquier `git push`, revisar que no se haya agregado por error ningún archivo
  con password/token (`.ini`, `.env`, claves) — `git status --short` antes de `git add`.

## 6. Firebase — proyecto propio, JSON plano desde GitHub Pages
- Proyecto Firebase (`isabel-riquelme-merma`) independiente de `ferreteria-oviedo` — nunca reusar.
- **Flujo actual (desde V.35 / 2026-08-27):** los JSON de bodegas se fetchean en texto plano
  desde GitHub Pages (no hay Firestore de datos). Solo Firestore `merma` sigue en uso.
- La autenticación Firebase Auth sí sigue activa — el HTML carga los JSON solo después de login.
- Para actualizar datos: correr los 5 scripts Python → `git add` archivos JSON → `git push`.
  No hay paso de subir a Firestore para los datos de bodegas.
- `_service_account.json` gitignored. `_subir_firestore_chunked.py` movido a `_ARCHIVO_HISTORICO/`.

## 7. Publicación pública
- El usuario decidió explícitamente publicar el reporte completo (incluye usuarios,
  estación/PC, observaciones, costos) en GitHub Pages. No volver a preguntar esto salvo
  que el usuario cambie el alcance.
- Todo cambio en el HTML/JSON publicado se sube con commit + push inmediatamente
  (no dejar cambios sin publicar "para después").
