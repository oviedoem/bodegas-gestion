---
name: debate
description: "Panel de gobernanza con 4 voces antes de una decisión significativa. Convoca: Socrático (problema real), Prompt Engineer (encuadre correcto), Abogado del Diablo (qué puede fallar), Abogado del Ángel (por qué vale la pena). TRIGGER: usuario dice 'no sé si hacer esto', 'evalúa', 'debate', 'decide por mí', o ante cambios que afecten múltiples sucursales, el esquema JSON, la subida a Firestore, o la estructura del HTML publicado."
---

# Skill: Debate — Panel de Gobernanza

Antes de ejecutar un cambio grande, convoca las 4 voces.
El objetivo es **descubrir lo que no ves**, no validar lo que ya decidiste.

## Cuándo usar

- Agregar una nueva sucursal al proyecto (IDs no verificados, riesgo de datos cruzados)
- Cambiar el esquema de `bodegas_ir_otras.json` o `bodegas_gestion.json` (el HTML los consume con estructura fija)
- Intentar migrar bodegas de vuelta a Firestore (quota, esquema chunked, autenticación)
- Modificar el flujo de autenticación Firebase (login del usuario `riquelme`)
- Cuando el usuario duda y pide segunda opinión

## Cuándo NO usar

- Scripts de descarga puntuales con IDs ya verificados → safe-change directo
- Fixes de typos o textos en el HTML
- Tareas con solución ya acordada en la sesión

---

## Las 4 Voces — ejecutar en orden

### 🔍 VOZ 1 — Socrático
*¿Estamos resolviendo el problema correcto?*

- ¿Qué problema exacto resuelve esto?
- ¿Hay síntoma vs. causa raíz?
- ¿Qué pasaría si NO hacemos este cambio?
- ¿Podría resolverse con una consulta puntual en vez de un cambio estructural?

### 📐 VOZ 2 — Prompt Engineer
*¿Está bien encuadrada la tarea?*

- ¿El pedido es suficientemente específico (sucursal, bodega, rango de fechas)?
- ¿Los IDs de bodega/sucursal están verificados en `IDS_REFERENCIA_*.md`?
- ¿El alcance está claro? ¿Afecta 1 sucursal o todas?
- Reformulación recomendada si hay ambigüedad

### 😈 VOZ 3 — Abogado del Diablo
*¿Qué puede salir mal?*

- ¿El cambio puede cruzar datos de sucursales? (ID equivocado = stock del lugar equivocado)
- ¿El cambio escribe a Firestore? (quota agotada → script colgado)
- ¿El cambio puede exponer credenciales SQL o el idToken de `riquelme`?
- ¿El cambio modifica archivos fuera de `E:\BODEGAS GESTION\`?
- ¿El JSON resultante es compatible con el HTML que lo consume?

### 😇 VOZ 4 — Abogado del Ángel
*¿Por qué vale la pena de todas formas?*

- Beneficio concreto para las personas de bodega
- Por qué el riesgo es manejable
- Alternativas consideradas y por qué esta es mejor
- ¿Pasa el filtro del CRITERIO.md? (aislamiento, credenciales, IDs verificados)

---

## Síntesis

```
RECOMENDACIÓN: [HACER / NO HACER / HACER CON AJUSTE]

Razón: [una línea]

Si HACER CON AJUSTE:
  Ajuste: [qué cambia en la propuesta]

Próximo paso si se aprueba:
  [primera acción concreta + script + sucursal]
```

---

## Regla de uso

El debate informa — la decisión final es del usuario.
Si el usuario confirma → aplicar safe-change antes de ejecutar.
