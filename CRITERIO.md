# CRITERIO.md — Bodegas Gestion (Multi-Sucursal)
# El "cerebro" del agente: criterios de decisión antes de ejecutar.
# Este archivo dice POR QUÉ y CUÁNDO — CLAUDE.md dice CÓMO.

## QUÉ ES ESTE ARCHIVO

`CLAUDE.md` describe instrucciones técnicas y procedimientos.
Este archivo describe los **criterios de juicio** que el agente aplica cuando hay una decisión que tomar.

---

## JERARQUÍA DE DECISIÓN

En orden de prioridad. Si hay conflicto, gana el nivel más alto:

1. **Nunca editar otros proyectos** — este repo es independiente; solo se LEE de El Manzano/Las Cabras/etc.
2. **Credenciales fuera de código y git** — la clave de login vive SOLO en `_CREDENCIAL_LOGIN_NO_SUBIR.txt`
3. **Sin write masivo a Firestore** — quota Spark agotada; bodegas van a JSON estático, no a Firestore
4. **VPN activa antes de SQL** — sin VPN, la conexión a 200.6.118.110 falla silenciosamente
5. **Un cambio a la vez** — un prompt = un script o una sucursal; nunca agregar scope no pedido

---

## CRITERIOS DE ACEPTACIÓN DE UN CAMBIO

| Criterio | Pregunta |
|---|---|
| **Aislamiento de proyecto** | ¿El cambio toca o modifica algún archivo fuera de `E:\BODEGAS GESTION\`? |
| **Sin credenciales en código** | ¿El script nuevo imprime o loggea la clave, el idToken o la IP? |
| **Sin write masivo Firestore** | ¿El cambio escribe más de 100 documentos a Firestore? |
| **IDs verificados** | ¿Los IDs de sucursal/bodega vienen de `IDS_REFERENCIA_*.md`, no inventados? |
| **VPN considerada** | ¿El script que llama a SQL Server asume que la VPN puede no estar activa? |

---

## CUÁNDO DECIR NO SIN PREGUNTAR

- Modificar cualquier archivo fuera de `E:\BODEGAS GESTION\` (regla de oro)
- Imprimir o loggear `_CREDENCIAL_LOGIN_NO_SUBIR.txt`, contraseñas o tokens en cualquier formato
- Escribir a Firestore colecciones `bodegas` o `bodegas_gestion` directamente (quota agotada)
- Usar IDs de sucursal o bodega no verificados en `IDS_REFERENCIA_*.md`
- Commitear archivos `.txt` de credenciales o JSON con datos sensibles

---

## CUÁNDO PEDIR CONFIRMACIÓN

- Agregar una nueva sucursal al proyecto (implica verificar IDs en ERP primero)
- Cambiar el esquema de los JSON estáticos (puede romper el HTML que los consume)
- Migrar colecciones de JSON estático de vuelta a Firestore (requiere solución "chunked")
- El cambio genera un archivo nuevo que podría quedar trackeado en git sin querer

---

## FILOSOFÍA DE FONDO

**Este proyecto es un observador, no un modificador.**

Los scripts LEEN del ERP (SQL Server, solo lectura) y PUBLICAN datos para que las personas de bodega los consulten.
Nunca escriben de vuelta al ERP. Nunca modifican datos de otras sucursales desde aquí.

**Multi-sucursal = múltiples oportunidades de confundir IDs.**
Un ID de bodega equivocado muestra stock de la sucursal incorrecta — error silencioso con consecuencias operativas.
Cada ID se verifica en `IDS_REFERENCIA_*.md` antes de usarlo en un query.

**La independencia del proyecto es su principal garantía de integridad.**
Si este proyecto empieza a depender de archivos de `ferreteria-oviedo`, deja de ser auditable de forma aislada.
