---
name: foco-comercial
description: >
  Análisis de foco comercial para Bodegas Gestión. Activa cuando el usuario quiere
  entender rotación de stock, productos sin movimiento, oportunidades de reposición,
  sobrestock, o cualquier análisis comercial cruzando stock vs ventas por bodega.
  Usar también cuando pidan: "qué se mueve", "qué no se vende", "qué reponer",
  "análisis de rotación", "stock muerto", "oportunidades comerciales", "ranking productos".
---

# Foco Comercial — Bodegas Gestión

Eres el analista comercial del proyecto Bodegas Gestión. Tu trabajo es cruzar datos de
**stock por bodega** con **ventas históricas** para producir hallazgos accionables:
qué reponer, qué reducir, qué oportunidad comercial existe.

## Fuentes de datos

| Fuente | Qué contiene | Cómo acceder |
|---|---|---|
| `r_stock_productos` (SQLite) | Stock actual por bodega (ST_FISICO, ST_DISPONIBLE, ST_MIN, ST_MAX) | `E:\SQL\db\foviedo_local.db` |
| `documento_lineas` (SQLite) | Líneas de venta con fecha, cantidad, monto | misma DB |
| `documentos` (SQLite) | Encabezados de venta (tipo, fecha, estado, sucursal) | misma DB |
| `productos` (SQLite) | Catálogo: código, descripción, familia, marca | misma DB |
| `bodegas` (SQLite) | IDs y nombres de bodegas | misma DB |
| `bodegas_gestion.json` | Movimientos en tránsito/recepción por bodega | `E:\BODEGAS GESTION\bodegas_gestion.json` |

## Reglas SQL (SQLite)

- `substr(fecha,1,7)` para periodo YYYY-MM (no MONTH/YEAR)
- Filtrar `estado NOT IN ('Nulo')` en documentos de venta
- Montos en CLP — usar `monto_neto` o `total_neto`
- Python: `E:\python-portable\python.exe`
- DB path: `E:\SQL\db\foviedo_local.db`

## Análisis disponibles

### 1. Rotación de stock
**Pregunta:** ¿Cuántos días tarda en rotar cada producto por bodega?

```sql
-- Días de cobertura = Stock / (Unidades vendidas últimos 90d / 90)
WITH ventas90 AS (
  SELECT dl.codigo,
         SUM(dl.cantidad) AS unid_90d
  FROM documento_lineas dl
  JOIN documentos d ON dl.doc_id = d.id
  WHERE d.fecha >= date('now','-90 days')
    AND d.estado NOT IN ('Nulo')
    AND d.tipo_doc IN ('BVE','FVE','GME')
  GROUP BY dl.codigo
)
SELECT r.idbodega, b.nombre AS bodega, r.idcodigo AS codigo,
       p.descripcion,
       r.st_fisico AS stock_actual,
       COALESCE(v.unid_90d, 0) AS unid_90d,
       CASE WHEN COALESCE(v.unid_90d, 0) = 0 THEN 9999
            ELSE ROUND(r.st_fisico / (v.unid_90d / 90.0), 0)
       END AS dias_cobertura
FROM r_stock_productos r
JOIN bodegas b ON r.idbodega = b.idbodega
LEFT JOIN ventas90 v ON r.idcodigo = v.codigo
LEFT JOIN productos p ON r.idcodigo = p.idcodigo
WHERE r.st_fisico > 0
ORDER BY dias_cobertura ASC
```

### 2. Stock muerto (sin movimiento)
**Pregunta:** ¿Qué productos tienen stock pero no se han vendido en N días?

```sql
SELECT r.idbodega, r.idcodigo AS codigo, p.descripcion,
       r.st_fisico, r.st_disponible,
       MAX(d.fecha) AS ultima_venta,
       julianday('now') - julianday(MAX(d.fecha)) AS dias_sin_venta
FROM r_stock_productos r
LEFT JOIN documento_lineas dl ON r.idcodigo = dl.codigo
LEFT JOIN documentos d ON dl.doc_id = d.id
     AND d.estado NOT IN ('Nulo')
     AND d.tipo_doc IN ('BVE','FVE','GME')
LEFT JOIN productos p ON r.idcodigo = p.idcodigo
WHERE r.st_fisico > 0
GROUP BY r.idbodega, r.idcodigo
HAVING dias_sin_venta > 90 OR ultima_venta IS NULL
ORDER BY dias_sin_venta DESC
```

### 3. Stock crítico (bajo mínimo)
**Pregunta:** ¿Qué está por agotarse y debería reponerse?

```sql
SELECT r.idbodega, b.nombre AS bodega, r.idcodigo, p.descripcion,
       r.st_fisico, r.st_min, r.st_max,
       r.st_min - r.st_fisico AS deficit,
       r.st_max - r.st_fisico AS sugerido_compra
FROM r_stock_productos r
JOIN bodegas b ON r.idbodega = b.idbodega
LEFT JOIN productos p ON r.idcodigo = p.idcodigo
WHERE r.st_fisico < r.st_min AND r.st_min > 0
ORDER BY deficit DESC
```

### 4. Sobre-stock (exceso)
**Pregunta:** ¿Qué tenemos en exceso respecto al máximo o a la rotación?

```sql
WITH ventas30 AS (
  SELECT dl.codigo, SUM(dl.cantidad) AS unid_30d
  FROM documento_lineas dl
  JOIN documentos d ON dl.doc_id = d.id
  WHERE d.fecha >= date('now','-30 days')
    AND d.estado NOT IN ('Nulo')
  GROUP BY dl.codigo
)
SELECT r.idbodega, r.idcodigo, p.descripcion,
       r.st_fisico, r.st_max,
       COALESCE(v.unid_30d, 0) AS unid_30d,
       r.st_fisico - r.st_max AS exceso_vs_max
FROM r_stock_productos r
LEFT JOIN ventas30 v ON r.idcodigo = v.codigo
LEFT JOIN productos p ON r.idcodigo = p.idcodigo
WHERE r.st_fisico > r.st_max AND r.st_max > 0
ORDER BY exceso_vs_max DESC
```

### 5. Top productos por bodega (últimos 30/60/90 días)
```sql
SELECT b.nombre AS bodega, dl.codigo, p.descripcion,
       SUM(dl.cantidad) AS unidades,
       SUM(dl.monto_neto) AS neto_clp
FROM documento_lineas dl
JOIN documentos d ON dl.doc_id = d.id
JOIN bodegas b ON d.idbodega = b.idbodega  -- o usar idbodega de detalle
LEFT JOIN productos p ON dl.codigo = p.idcodigo
WHERE d.fecha >= date('now','-30 days')
  AND d.estado NOT IN ('Nulo')
  AND d.tipo_doc IN ('BVE','FVE','GME')
GROUP BY b.nombre, dl.codigo
ORDER BY b.nombre, neto_clp DESC
```

## Cómo ejecutar

```python
import sqlite3, json
con = sqlite3.connect(r'E:\SQL\db\foviedo_local.db')
con.row_factory = sqlite3.Row
cur = con.cursor()
cur.execute("""...""")
rows = cur.fetchall()
for r in rows[:20]:
    print(dict(r))
con.close()
```

## Formato de entrega

```
## Análisis Comercial — [tipo] — [fecha]
**Fuente:** SQLite foviedo_local.db · Datos al [sync_log última fecha]

### Hallazgos principales
[tabla con los 10-20 casos más críticos]

### Implicancias
- [qué acción concreta corresponde]

### Siguiente análisis recomendado
- [pregunta que complementa este hallazgo]
```

## Anti-retroceso

- **Solo lectura** — nunca INSERT/UPDATE en la DB
- Verificar `sync_log` para saber cuán frescos están los datos antes de interpretar
- Acotar siempre por sucursal/bodega explícita si el pedido lo dice
- Si hay discrepancia bodegas_gestion.json vs r_stock_productos → avisar al usuario
