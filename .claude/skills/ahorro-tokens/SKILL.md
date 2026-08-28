---
name: ahorro-tokens
description: Protocolo global de ahorro de tokens para maximizar la sesión semanal de 5 horas. No mezclar proyectos. Una tarea a la vez.
---

# Ahorro de Tokens — BODEGAS GESTION

Ver protocolo completo en: `C:\Users\alejandro\.claude\skills\ahorro-tokens\SKILL.md`
Ver también: skill `safe-change` en este mismo proyecto (`.claude\skills\safe-change\SKILL.md`).

## Reglas específicas de este proyecto

### No mezclar proyectos
- Solo editar en `E:\BODEGAS GESTION\`. Otros proyectos = solo lectura.
- Git push a `oviedoem/bodegas-gestion` — no a `E:\git-sync\`.
- Una tarea a la vez — confirmar antes de la siguiente.

### Archivos de referencia — leer ANTES de explorar SQL
- `IDS_REFERENCIA_IR.md` — IDs Isabel Riquelme
- `IDS_REFERENCIA_BODEGAS_GESTION.md` — IDs otras sucursales + CD
- `flujo-stock-justime.html` → sección Referencia ERP (columnas, documentos, bodegas)

### index.html supera 2000 líneas — nunca leer completo
- Usar `Grep` para ubicar secciones → `Read` con `offset+limit`.

### Deploy (siempre los dos pasos)
```powershell
git push
E:\npm-global\firebase.cmd deploy --only hosting --project isabel-riquelme-merma
```
URL autoritativa: `isabel-riquelme-merma.web.app` (GitHub Pages tiene ~10 min CDN delay).
