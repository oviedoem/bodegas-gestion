---
name: loop-sesion
description: "Guía la sesión a través del Loop 0-5: Arrancar → Abrir → Alinear → Ejecutar → Validar → Cerrar. Invocar al inicio (/loop-sesion 0) o para el siguiente paso (/loop-sesion N). TRIGGER: usuario dice 'empecemos', 'inicio sesión', 'arrancar', 'loop', 'qué sigue'."
---

# Skill: Loop de Sesión (0-5) — Bodegas Gestion

El agente trabaja en ciclos. Cada sesión sigue estos 6 pasos en orden.
Invocar `/loop-sesion [N]` para ejecutar ese paso. Sin número → mostrar estado actual.

---

## PASO 0 — ARRANCAR
*Cargar estado. No ejecutar nada todavía.*

1. `git log --oneline -5` — ver últimos cambios
2. Identificar pendientes de la sesión anterior (CLAUDE.md historial)
3. Leer CRITERIO.md — activar el "cerebro"
4. Verificar VPN activa si la sesión requiere SQL Server

```
ESTADO:
- Último cambio: [commit]
- Pendiente anterior: [item]
- VPN necesaria: [sí / no]
- Propuesta para hoy: [tarea]
```

---

## PASO 1 — ABRIR
*Definir el alcance. Una tarea por sesión.*

1. Usuario declara (o el agente propone) la tarea
2. Filtrar con CRITERIO.md:
   - ¿El cambio toca archivos fuera de `E:\BODEGAS GESTION\`? → NO sin confirmar
   - ¿El cambio escribe a Firestore `bodegas` / `bodegas_gestion`? → `/debate` primero
   - ¿El cambio agrega una sucursal nueva? → verificar IDs en ERP primero
   - ¿Es un script puntual con IDs verificados? → Paso 2

```
SESIÓN DE HOY:
Tarea: [una línea]
Sucursal/es afectadas: [IR / EM / SV / LC / LT / CD / todas]
Script: [generar_merma_ir.py | generar_bodegas_ir.py | otro]
Deploy necesario: [sí / no]
```

---

## PASO 2 — ALINEAR
*Acordar antes de ejecutar.*

```
TOCO:    [función o query exacto]
ARCHIVO: [generar_merma_ir.py | generar_bodegas_gestion.py | otro]
RAZÓN:   [una línea]
NO TOCO: [qué queda igual — especialmente otras sucursales]
```

Confirmar reglas CRITERIO.md:
- ¿Los IDs de sucursal/bodega provienen de `IDS_REFERENCIA_*.md`?
- ¿El script puede loggear credenciales o tokens?
- ¿El resultado es JSON estático (no Firestore write)?

**El usuario aprueba antes de pasar al Paso 3.**

---

## PASO 3 — EJECUTAR
*Hacer el trabajo. Un cambio a la vez.*

- Aplicar solo lo declarado en Paso 2
- Si aparece algo adicional → pausar, registrar, no tocar
- Recordar: este proyecto NO modifica archivos de otros proyectos

---

## PASO 4 — VALIDAR
*Probar antes de declarar listo.*

```bash
# Sintaxis Python
python -m py_compile [script modificado]

# Verificar JSON generado (estructura válida, no vacío)
python -c "import json; d=json.load(open('[archivo].json')); print(len(d), 'registros')"

# Ver HTML en navegador — verificar que el tab de la sucursal carga datos
# (abrir index.html localmente o desde GitHub Pages)
```

Si falla → volver al Paso 3. Si el HTML no carga datos → revisar estructura del JSON.

---

## PASO 5 — CERRAR

```bash
git add [archivos del alcance]
git status  # verificar sin archivos inesperados ni credenciales
git commit -m "[tipo]: [descripción]"
git push -u origin claude/claude-codex-os-system-hxard7
```

Si hubo cambios a `index.html` o JSON:
```powershell
# Deploy Firebase (desde E:\BODEGAS GESTION\)
firebase deploy --project isabel-riquelme-merma --only hosting
```

```
CIERRE:
Commit: [hash]
Hecho: [una línea]
Pendiente: [lista]
Próxima sesión: [primera acción]
```

---

## Reglas del loop

- No saltar pasos — un ID de bodega equivocado muestra datos de la sucursal incorrecta
- No acumular scope — lo nuevo va al CLAUDE.md, no a este loop
- No editar otros proyectos bajo ningún concepto
- El Paso 5 es obligatorio — sin commit, el cambio no existió
