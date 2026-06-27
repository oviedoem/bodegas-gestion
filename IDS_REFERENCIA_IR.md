# IDS_REFERENCIA_IR.md — Sucursal Isabel Riquelme
Verificado por consulta SQL directa el 2026-06-27. No editar a mano — re-consultar si cambia.

## Sucursal
| IDSUCURSAL | Nombre |
|:---:|---|
| **02** | **Isabel Riquelme** |

## Bodegas relevantes (P_BODEGAS, IDSUCURSAL='02')
| IDBODEGA | SIMBOLO | Nombre | Uso |
|:---:|:---:|---|---|
| **75** | **MIR** | Mermas Isabel Riquelme | ✅ bodega de merma (proyecto activo) |
| 69 | IIR | Ingreso Isabel Riquelme | Logística |
| 86 | SIR | Sala Isabel Riquelme | Comercial |
| 4 | PIR | Patio Isabel Riquelme | Comercial |
| 85 | EIR | Exhibición Isabel Riquelme | Auxiliar |
| 92 | RST | Recepción Santiago | Logística |

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

## Notas
- No existe una tabla de "log de usuario+computador" separada — el dato de usuario/estación
  vive directamente en `M_DOCUMENTOS_ENCABEZADO` por cada documento (no hay trazabilidad a
  nivel de línea/detalle, solo a nivel de documento completo).
- `ESTACION` es el nombre de host de la estación de trabajo (NetBIOS), no una IP.
