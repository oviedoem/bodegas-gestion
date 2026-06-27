---
name: safe-change
description: Reglas de cambio seguro y ahorro de tokens para el proyecto Isabel Riquelme (SQL Foviedo, reportes HTML, publicación GitHub). Usar antes de tocar generar_merma_ir.py, generar_bodegas_ir.py o el HTML publicado.
---

# safe-change — Isabel Riquelme

Reglas obligatorias para cualquier cambio en este proyecto (`E:\ISABEL RIQUELME\`).

## 1. No mezclar proyectos
- Solo se edita dentro de `E:\ISABEL RIQUELME\`. Otros proyectos (`E:\ferreteria-oviedo`,
  `W:\SUCURSAL LAS CABRAS`, `E:\git-sync`) son **solo lectura** — copiar y adaptar aquí,
  nunca modificar el original.
- El repo GitHub de este proyecto (`oviedoem/merma-isabel-riquelme`) es independiente del
  de El Manzano — nunca usar `E:\git-sync` para esto.

## 2. Ahorro de tokens — no re-explorar lo ya verificado
- IDs de sucursal/bodega/columnas SQL ya están en `IDS_REFERENCIA_IR.md`. No volver a
  correr `INFORMATION_SCHEMA.COLUMNS` si el dato ya está documentado ahí.
- Antes de escribir una consulta SQL nueva, revisar `generar_merma_ir.py` y
  `generar_bodegas_ir.py` — ambos ya tienen el patrón de JOIN correcto
  (R_STOCK_PRODUCTOS + M_PRODUCTOS + M_DOCUMENTOS_ENCABEZADO + catálogos de
  familia/marca). Reusar esa estructura, no reinventarla.
- Para cambios de UI (HTML/CSS/JS), el patrón de pestañas (`VISTAS` en el JS embebido)
  ya es genérico — agregar una bodega/vista nueva es agregar una entrada al diccionario
  `VISTAS`, no duplicar el bloque de funciones `render`/`filtrar`/`exportarExcel`.

## 3. Descargas SQL — por lotes pequeños
- Nunca bajar todas las bodegas en una sola consulta masiva. `generar_bodegas_ir.py` baja
  de a `LOTE_SIZE=2` bodegas con pausa entre lotes — seguir ese patrón si se agregan más
  bodegas, para evitar timeouts/conflictos en la conexión SQL compartida con el ERP.
- Verificar consistencia después de cada descarga: comparar `total códigos` por bodega
  contra un `COUNT(*)` directo en `R_STOCK_PRODUCTOS` antes de confiar en el resultado
  (ver bloque `RESUMEN / CONSISTENCIA POR BODEGA` que imprime el script).

## 4. Regla anti-retroceso (obligatoria en todo script de descarga)
- Si la nueva descarga trae menos del 50% de los registros del JSON anterior, abortar
  el sobrescrito y conservar el archivo anterior. Ya implementado en
  `generar_merma_ir.py` y `generar_bodegas_ir.py` — replicar este bloque en cualquier
  script de descarga nuevo.

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

## 6. Firebase — proyecto propio, datos solo tras login
- Proyecto Firebase de este reporte (`isabel-riquelme-merma`) es independiente del de
  `ferreteria-oviedo` — nunca reusar el mismo proyecto/Firestore.
- El HTML público en GitHub Pages NO debe volver a embeber datos crudos en el código
  fuente. Los datos viven en Firestore con reglas `auth != null`; el HTML solo carga
  datos después de que el usuario inicia sesión.
- Para actualizar datos: regenerar JSON con `generar_merma_ir.py`/`generar_bodegas_ir.py`,
  luego subir con `_subir_datos_firestore.py` (hace login con `riquelme`, clave leída
  del archivo local, nunca impresa).

## 6. Publicación pública
- El usuario decidió explícitamente publicar el reporte completo (incluye usuarios,
  estación/PC, observaciones, costos) en GitHub Pages. No volver a preguntar esto salvo
  que el usuario cambie el alcance.
- Todo cambio en el HTML/JSON publicado se sube con commit + push inmediatamente
  (no dejar cambios sin publicar "para después").
