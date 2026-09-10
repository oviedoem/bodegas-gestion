# revisar-cambio — BODEGAS GESTION

Revisión de $0 (sin llamadas a API) antes de dar por cerrado cualquier cambio en este
proyecto. Se aplica junto con `safe-change` y `ahorro-tokens`, no las reemplaza.
Correr esta checklist mentalmente (o literal, grep en mano) antes de cada commit.

## Checklist obligatoria antes de cerrar un cambio

1. **Alcance** — ¿el cambio tocó SOLO archivos dentro de `E:\BODEGAS GESTION\`?
   Ningún archivo de `E:\ferreteria-oviedo`, `W:\`, `E:\SQL\` fue editado (solo lectura).
2. **Credenciales** — `git status --short` revisado antes de `git add`. Ningún `.ini`,
   `.env`, password, IP o token quedó en un archivo staged. `_service_account.json`
   sigue en `.gitignore`.
3. **VISTAS dict** — si se tocó `index.html`: toda vista nueva usa `initVista`/`render`
   estándar, o fue agregada explícitamente al filtro `VISTAS_STD`
   (`Object.keys(VISTAS).filter(v => v !== 'solicitud_lc')`). No se duplicó lógica de
   render/filtrar/export por bodega.
4. **Anti-retroceso** — si se tocó un script de descarga: mantiene el bloque que aborta
   si trae <50% de los registros del JSON anterior. No se sobrescribió un JSON sin ese check.
5. **Consistencia de datos** — tras regenerar un JSON, sumar los sub-totales
   (por sucursal/bodega) y confirmar que igualan el `total` declarado en el archivo.
   No dar por bueno un JSON nuevo sin este chequeo aritmético.
6. **Modo restringido (SV/LC)** — si el cambio afecta datos que `MODO_SV`/`MODO_LC`
   consumen (`data/bodegas-sv.json`, `data/bodegas-lc.json`, `data/stock-critico-lc.json`,
   `data/oc-pend-resumen-lc.json`), verificar que también quedaron regenerados en la
   misma pasada — no solo el dataset de admin. Esta fue la causa raíz del bug encontrado
   el 09-09-2026 (datos de SV/LC 12 días más viejos que los del admin, sin que ningún
   script los regenerara).
7. **Archivos huérfanos** — no dejar JSON/HTML de prueba sueltos en la raíz ni en `data/`.
   Si algo queda obsoleto, mover a `_ARCHIVO_HISTORICO/` (no borrar sin confirmar).
8. **Documentación** — si el cambio afecta el flujo descrito en `AGENTS.md`, `CLAUDE.md`
   o `pipeline-bodegas-gestion.html`, actualizar esos archivos en el mismo cierre de
   sesión — no dejarlo "para después" (causa de la desalineación AES-256 encontrada
   09-09-2026: el flujo cambió el 27-08 pero `AGENTS.md` no se actualizó hasta hoy).
9. **Memoria de sesión** — si se hizo un cambio de fondo (no solo datos frescos),
   dejar o actualizar `memory/estado-sesion-YYYYMMDD.md` con qué cambió y por qué.
10. **Deploy** — commit + push + `firebase deploy --only hosting --project
    isabel-riquelme-merma` en la misma pasada si el cambio toca HTML/JSON publicado
    (regla ya vigente en `CLAUDE.md`, sección Publicación — no volver a preguntar
    salvo que cambie el alcance).

## Cuándo NO alcanza esta skill

- Cambios que tocan credenciales SQL, esquema Firestore, o reglas de seguridad:
  requieren confirmación explícita del usuario aunque pasen esta checklist.
- Cambios que afectan a más de un proyecto (nunca debería pasar — ver Regla de Oro
  en `CLAUDE.md`).
