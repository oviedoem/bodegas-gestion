# IDS_REFERENCIA_BODEGAS_GESTION.md — Proyecto BODEGAS GESTION (multi-sucursal)
Verificado por consulta SQL directa (`P_BODEGAS`) el 2026-07-21. No editar a mano —
re-consultar con `verificar_bodegas_gestion.py` si cambia el ERP.

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
