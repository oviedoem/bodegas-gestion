# IDS_REFERENCIA_BODEGAS_GESTION.md — Proyecto BODEGAS GESTION (multi-sucursal)
Verificado por consulta SQL directa (`P_BODEGAS`) el 2026-07-21. No editar a mano —
re-consultar con `verificar_bodegas_gestion.py` si cambia el ERP.

## Actualización 2026-07-21 (v2) — categorías ampliadas
Tras revisión de consistencia contra el catálogo completo de `P_BODEGAS` para las 5
sucursales, se agregaron categorías nuevas pedidas por el usuario:
- **Logística**: Recepción, Ingreso, Tránsito, Distribución, Despacho Proveedor.
- **Auxiliar**: Gestión, Merma, Garantía, Remate, Marketing, + casos puntuales
  (Consumo San Vicente, Volumen Las Cabras).
- **Exhibición**: incluida para las 5 sucursales (antes excluida como "Comercial") —
  ver nota de volumen abajo, son bodegas MUY grandes.
- **Facturación** (Bodega Ferretería=20, Casa Central=1, Ferreteria=2, etc.):
  confirmado que se mantienen EXCLUIDAS — no son de ninguna sucursal individual.

### Gap corregido
- **Garantía Las Cabras** (GFL, IDBODEGA=91) faltaba — agregada a
  `generar_bodegas_gestion.py`. Isabel Riquelme ya tenía la suya (GAR=53) en
  `generar_bodegas_ir.py`.

### Bodegas atípicas incluidas (no encajan 100% en las categorías estándar)
| IDBODEGA | Símbolo (ERP) | Nombre | Sucursal | Categoría asignada |
|:---:|:---:|---|---|---|
| 43 | CSV (duplicado con Calzada=44) | Consumo San Vicente | 05 | Auxiliar |
| 97 | VLC | Volumen Las Cabras | 06 | Auxiliar |

⚠️ **Consumo San Vicente (43) y Calzada San Vicente (44) comparten el mismo
`SIMBOLO_BODEGA` ("CSV") en el ERP** — son bodegas distintas. Cualquier script que
identifique bodegas por símbolo en vez de IDBODEGA las va a confundir. Se corrigió
`generar_bodegas_gestion.py` para indexar internamente por IDBODEGA, no por símbolo.

### Exhibición — volumen alto (no es error)
Las bodegas de Exhibición concentran muchísimo stock valorizado (vitrina/showroom):
EEM=1819 códigos, ESV=1786, ELC=1411, ELE=1523, EIR=2090. Es esperado — es donde vive
el stock "en exhibición, valorizado pero no disponible para venta regular".

### Bodegas compartidas/globales — ampliado
Antes solo Centro de Distribución (CD=23). Se agregaron, mismo criterio (bodega única,
no repetida por sucursal, vive bajo un IDSUCURSAL administrativo distinto):

| IDBODEGA | Símbolo | Nombre | IDSUCURSAL real (ERP) |
|:---:|:---:|---|:---:|
| 23 | CD | Centro de Distribucion | 08 |
| 98 | BDP | Despacho Proveedor | 09 (Ventas Empresas) |
| 84 | REM | Remate | 01 (Casa Matriz) |
| 36 | MKT | Marketing | 01 (Casa Matriz) |

Nota: existe una bodega "Despacho Proveedor - NO USAR" (IDBODEGA=17, IDSUCURSAL=01)
marcada explícitamente por el ERP para no usar — excluida a propósito.

### Categorías descritas por el usuario pero NO agregadas como bodegas nuevas
- **Ingreso**: ya cubierto (categoría original).
- **Dormidas** (sin ingreso >90 días): no es una bodega, es un criterio de antigüedad
  ya soportado por el campo `diasAntiguedad`/clase CSS `.d90` en el HTML (resalta en
  rojo). Si se quiere un KPI dedicado "Dormidas" (conteo de códigos ≥90 días), falta
  agregarlo — no se hizo en esta pasada.

Complementa (no reemplaza) `IDS_REFERENCIA_IR.md`, que documenta el detalle propio de
Isabel Riquelme (Firebase, MERMA.xlsx, notas de folio vacío, stock negativo, etc.).

## Alcance de sucursales
El Manzano (04), Isabel Riquelme (02), San Vicente (05), Las Cabras (06), Litueche (11).

## Criterio de bodegas a incluir
Solo categorías de gestión interna — **Gestión, Merma, Recepción, Ingreso, Tránsito,
Calzada** — nunca bodegas comerciales/de facturación (Sala, Patio, Exhibición, Garantía,
Retiro Web, Servicio Técnico, etc.).

**Excepción pedida por el usuario:** Calzada de **El Manzano se excluye** (el resto de
sucursales sí la incluye).

## Bodegas por sucursal (verificado SQL 2026-07-21)

### 02 — Isabel Riquelme
| IDBODEGA | Símbolo | Nombre | Categoría |
|:---:|:---:|---|---|
| 30 | GO | Gestion Isabel Riquelme | Gestión |
| 75 | MIR | Mermas Isabel Riquelme | Merma |
| 92 | RST | Recepcion Santiago | Recepción |
| 69 | IIR | Ingreso Isabel Riquelme | Ingreso |
| 5 | CAL | Calzada | Calzada |
| — | — | (sin bodega Tránsito) | Tránsito |
| 87 | DIR | Distribucion Isabel Riquelme | Distribución (ver nota) |

### 04 — El Manzano
| IDBODEGA | Símbolo | Nombre | Categoría |
|:---:|:---:|---|---|
| 28 | GEM | Gestion El Manzano | Gestión |
| 29 | MEM | Mermas El Manzano | Merma |
| 55 | RCE | Recepcion El Manzano | Recepción |
| 72 | IEM | Ingreso El Manzano | Ingreso |
| 46 | TEM | Transito El Manzano | Tránsito |
| — | — | Calzada El Manzano — **excluida a pedido del usuario** | Calzada |
| — | — | (sin bodega Distribución) | Distribución |

### 05 — San Vicente
| IDBODEGA | Símbolo | Nombre | Categoría |
|:---:|:---:|---|---|
| 41 | GSV | Gestion San Vicente | Gestión |
| 42 | MSV | Mermas San Vicente | Merma |
| 56 | RSV | Recepcion San Vicente | Recepción |
| 70 | ISV | Ingreso San Vicente | Ingreso |
| 45 | TSV | Transito San Vicente | Tránsito |
| 44 | CSV | Calzada San Vicente | Calzada |
| 88 | DSV | Distribucion San Vicente | Distribución (ver nota) |

### 06 — Las Cabras
| IDBODEGA | Símbolo | Nombre | Categoría |
|:---:|:---:|---|---|
| 37 | GLC | Gestion Las Cabras | Gestión |
| 38 | MLC | Mermas Las Cabras | Merma |
| 57 | RLC | Recepcion Las Cabras | Recepción |
| 71 | ILC | Ingreso Las Cabras | Ingreso |
| 16 | TLC | Transito Las Cabras | Tránsito |
| 35 | CLC | Calzada Las Cabras | Calzada |
| — | — | (sin bodega Distribución) | Distribución |

### 11 — Litueche
| IDBODEGA | Símbolo | Nombre | Categoría |
|:---:|:---:|---|---|
| 63 | GLE | Gestion Litueche | Gestión |
| 76 | MLE | Mermas Litueche | Merma |
| — | — | (sin bodega Recepción) | Recepción |
| 74 | ILE | Ingreso Litueche | Ingreso |
| 59 | TLE | Transito Litueche | Tránsito |
| 78 | CLT | Calzada Litueche | Calzada |
| 79 | DLT | Distribucion Litueche | Distribución (ver nota) |

## Compartida (una sola vez, no repetida por sucursal)
| IDBODEGA | Símbolo | Nombre | IDSUCURSAL real (ERP) |
|:---:|:---:|---|:---:|
| 23 | CD | Centro de Distribucion | 08 (auxiliar/compartida para todas) |

## Nota importante — bodegas "Distribución"
Las bodegas `Distribucion <Sucursal>` **no están registradas bajo el IDSUCURSAL de esa
sucursal en el ERP** — viven bajo sucursales administrativas distintas:

| IDBODEGA | Símbolo | Nombre | IDSUCURSAL real (ERP) |
|:---:|:---:|---|:---:|
| 87 | DIR | Distribucion Isabel Riquelme | **14** (Distribucion) |
| 88 | DSV | Distribucion San Vicente | **14** (Distribucion) |
| 79 | DLT | Distribucion Litueche | **09** (Ventas Empresas) |

Por pedido explícito del usuario se incluyen igual, asociadas a la sucursal que indica
su nombre — **las queries deben filtrar por `IDBODEGA` directo**, no por
`WHERE IDSUCURSAL='02'/'05'/'11'` (esas queries NO las van a traer). El Manzano y Las
Cabras no tienen bodega Distribución propia.

## Herramienta de verificación
`verificar_bodegas_gestion.py` — consulta `P_BODEGAS` en vivo (solo lectura) para las 5
sucursales objetivo y filtra por nombre de categoría. Re-ejecutar si se necesita
re-verificar tras cambios en el ERP. No incluye aún Centro de Distribucion / Distribucion
en su filtro automático (esas se agregaron a mano en este documento tras confirmar con
el usuario) — pendiente si se quiere, ampliar el script para cubrirlas también.

## Fuente / credenciales
Igual que el resto del proyecto: `E:\ferreteria-oviedo\credenciales_db.ini` (solo
lectura, nunca se copia el valor). Ver `IDS_REFERENCIA_IR.md` para detalle de columnas
de movimientos (`M_DOCUMENTOS_DETALLE`, `M_DOCUMENTOS_ENCABEZADO`, etc.) — se reutiliza
el mismo patrón de queries para todas las sucursales.
