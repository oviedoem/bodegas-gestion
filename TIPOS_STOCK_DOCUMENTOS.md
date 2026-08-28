# Comportamiento de Stock por Tipo de Documento — JustTime ERP

Fuente: `Foviedo.dbo.M_DOCUMENTOS` — consultado 2026-08-28

## Flags clave

| Flag | Significado |
|------|-------------|
| `TIPOOPERACION` | `I` = Ingreso (entra a bodega), `C` = Consumo/Salida |
| `ESTRANSITORIO` | `True` = mueve Tránsito; afecta stock en dos pasos (GIB → GRT) |
| `ESDESPACHO` | `True` = afecta Físico directamente |
| `AFECTA_CAMBIOBODEGA` | `True` = involucra traslado entre bodegas |

## Tabla de documentos

| DOC | TIPOSTOCK | TIPOOPER | CAMBIOBOD | TRANSIT | DESPACHO | Impacto stock |
|-----|-----------|----------|-----------|---------|----------|---------------|
| BVE | St_Contable | C | No | No | No | Disp− |
| FVE | St_Contable | C | Sí | No | No | Disp− |
| GIB | St_Contable | I | Sí | Sí | Sí | **−Fis en ORIGEN** (confirmación despacho; genera GRT en destino) |
| GRT | St_Contable | I | Sí | Sí | Sí | **+Fis en DESTINO** (confirma llegada) |
| GET | St_Contable | I | Sí | Sí | Sí | **−Fis en ORIGEN** (egreso de traslado, genera GRT en destino) |
| GME | St_DevVen | C | Sí | Sí | Sí | Fis− (despacho físico final) |
| GRC | St_DevCom | P | Sí | Sí | No | Devolución compra: Disp+, Fis+ |
| NCE | St_Contable | C | Sí | No | No | Nota crédito electrónica: Disp+ |
| NVM | St_Pedido | C | No | Sí | No | Nota venta mayorista: Disp− (pedido) |
| VMN | St_Pedido | C | Sí | Sí | No | Venta mayorista: Disp− |
| Gdc | St_DevCom/St_Consignado | P/C | Sí | Sí | Mixto | Consignación |

## Lógica de reconstrucción de Físico

```
TIPOOPERACION=I + ESTRANSITORIO=False → Fis+ (recepción directa: GII, GRC, etc.)
GRT en destino                         → +Fis en destino (confirmación de llegada)
GIB en origen                          → −Fis en origen (confirmación de salida; IDBODEGA=bodega origen)
GET en origen                          → −Fis en origen (egreso traslado; IDBODEGA=bodega origen)
TIPOOPERACION=C + ESDESPACHO=True     → Fis−  (GME: despacho físico final)
TIPOOPERACION=C + ESDESPACHO=False    → Disp− únicamente (BVE/FVE)
```

> **Verificado por investigación 26129 CSV (2026-08-28):** GIB 9880 (bod=44, cant=21) y GET 259/1229 (bod=44, 1+1) son egresos de CSV.  
> Con esta lógica: 100(GRT) − 77(GME) − 21(GIB) − 1(GET) − 1(GET) = **0**. ERP reporta −1 (brecha residual de 1 unidad, posiblemente stock inicial pre-2017).

## Línea de detalle: ¿qué bodega registra cada doc?

- **GIB**: `IDBODEGA` en detalle = bodega de **origen** (la que ENVÍA → −Fis aquí)
- **GRT**: `IDBODEGA` en detalle = bodega de **destino** (la que RECIBE → +Fis aquí)
- **GET**: `IDBODEGA` en detalle = bodega de **origen** (egreso traslado → −Fis aquí)
- **GME**: `IDBODEGA` en detalle = bodega que **despacha** (físico sale de ahí → −Fis)
- **BVE/FVE**: `IDBODEGA` en detalle = bodega de **venta** (solo −Disp)

## Ciclo Calzada (stock negativo permitido, bod=44 CSV)

1. BVE/FVE → Disp− (puede quedar negativo)
2. GRT (llegada del producto) → Disp↑ a 0, Fis+ al total recibido
3. GME → Fis− (cierra físico, Dif=0)

Diferencia positiva (Disp=0, Fis>0) entre GRT y GME es **estado normal**, no error.
