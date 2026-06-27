# IDS_REFERENCIA_IR.md — Sucursal Isabel Riquelme
Verificado por consulta SQL directa el 2026-06-27. No editar a mano — re-consultar si cambia.

## Sucursal
| IDSUCURSAL | Nombre |
|:---:|---|
| **02** | **Isabel Riquelme** |

## Bodegas relevantes (P_BODEGAS, IDSUCURSAL='02')
| IDBODEGA | SIMBOLO | Nombre | Uso |
|:---:|:---:|---|---|
| **75** | **MIR** | Mermas Isabel Riquelme | ✅ menú "Merma" — `generar_merma_ir.py` |
| 5 | CAL | Calzada | ✅ menú "Otras Bodegas" — `generar_bodegas_ir.py` |
| 6 | SER | Servicio Tecnico | ✅ menú "Otras Bodegas" |
| 25 | WEB | Retiro Web Santiago | ✅ menú "Otras Bodegas" |
| 30 | GO | Gestion Isabel Riquelme | ✅ menú "Otras Bodegas" |
| 53 | GAR | Garantia Santiago | ✅ menú "Otras Bodegas" |
| 69 | IIR | Ingreso Isabel Riquelme | ✅ menú "Otras Bodegas" |
| 77 | BMC | Marticorena Stgo | ✅ menú "Otras Bodegas" |
| 92 | RST | Recepción Santiago | ✅ menú "Otras Bodegas" (0 códigos con stock al 2026-06-27) |
| 99 | HEL | Herramientas Electricas | ✅ menú "Otras Bodegas" |
| 86 | SIR | Sala Isabel Riquelme | Comercial (no incluida en reportes) |
| 4 | PIR | Patio Isabel Riquelme | Comercial (no incluida en reportes) |
| 85 | EIR | Exhibición Isabel Riquelme | Auxiliar (no incluida en reportes) |

Conteos verificados por `COUNT(*) FROM R_STOCK_PRODUCTOS WHERE IDBODEGA=? AND IDSUCURSAL='02'
AND ST_FISICO>=1` al 2026-06-27: CAL=699, SER=10, WEB=32, GO=51, GAR=30, IIR=85, BMC=73,
RST=0, HEL=263 — coinciden exactamente con los códigos generados por `generar_bodegas_ir.py`.

## Catálogos de clasificación (para familia/marca en bodegas sin Excel de referencia)
`M_PRODUCTOS` solo tiene IDs (`IDHIPERFAMILIA`, `IDFAMILIA`, `IDSUBFAMILIA`, `IDMARCA`) — el
texto se obtiene con JOIN a:
- `P_HIPERFAMILIAS` (IDHIPERFAMILIA → HIPERFAMILIA)
- `P_FAMILIAS` (IDFAMILIA + IDHIPERFAMILIA → FAMILIA)
- `P_SUBFAMILIAS` (IDSUBFAMILIA + IDFAMILIA + IDHIPERFAMILIA → SUBFAMILIA)
- `P_MARCAS` (IDMARCA → MARCA)

(En `generar_merma_ir.py` no se necesitó este join porque `MERMA.xlsx` ya traía esas
columnas en texto desde el ERP.)

## Tablas SQL usadas
- `Foviedo.dbo.R_STOCK_PRODUCTOS` — stock actual (ST_FISICO, ST_DISPONIBLE) por bodega/código.
- `Foviedo.dbo.M_PRODUCTOS` — descripción, costo promedio.
- `Foviedo.dbo.M_DOCUMENTOS_DETALLE` + `Foviedo.dbo.M_DOCUMENTOS` — movimientos de entrada
  (GRC, GRT, GME, GIB, Gdc, GII, GTS, GEI, GST, etc.) por código/bodega.
- `Foviedo.dbo.M_DOCUMENTOS_ENCABEZADO` — encabezado del documento. Columnas clave:
  - `IDRESPONZABLE`, `AUTORIZADO_FIRMA`, `IDVENDEDOR` → **usuario** que generó/autorizó el movimiento.
  - `ESTACION` → **nombre de equipo/PC** donde se emitió el documento (ej. `RROJAS-NOTE`, `CAJASANTIAGO-PC`).
  - `FECHA_REGISTRO` → fecha y hora exacta de registro en el sistema (timestamp completo).
- `Foviedo.dbo.M_Documentos_Encabezado_Observacion` — `OBSERVACION_IMPRESA` (motivo/observación
  escrita por el usuario al emitir el documento, ej. "merma de IR hasta el dia 26 de enero").

## Credenciales
Archivo: `E:\ferreteria-oviedo\credenciales_db.ini` (solo lectura, NUNCA copiar el valor del
password a esta carpeta). Driver: `{SQL Server}`, requiere `TrustServerCertificate=yes`.

## Folio vacío en algunos tipos de documento (verificado, no es bug del script)
Para tipos de documento internos de ajuste/traslado entre bodegas (**GIB, GEI, GII**, y a
veces GME/GDV/Gdc) la columna `M_DOCUMENTOS_DETALLE.NUMERO` viene **0/vacía directamente
desde el ERP** — solo `GRT` (Recepción Traslado) y `GRC` (Recepción Compra) traen folio
real. Confirmado con consulta directa a `M_DOCUMENTOS_DETALLE` filtrando por código y
bodega: las filas GET/GII/GEI/GIB tienen `NUMERO=0` mientras la fila GRT del mismo
producto sí trae folio (ej. 99898). En el HTML se muestra `s/nº` en vez de un valor vacío
o "0" para que quede claro que es un dato esperado, no un error de carga.

## Notas
- No existe una tabla de "log de usuario+computador" separada — el dato de usuario/estación
  vive directamente en `M_DOCUMENTOS_ENCABEZADO` por cada documento (no hay trazabilidad a
  nivel de línea/detalle, solo a nivel de documento completo).
- `ESTACION` es el nombre de host de la estación de trabajo (NetBIOS), no una IP.
