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
| GIB | St_Contable | I | Sí | Sí | Sí | Trans+ en destino (bod que recibe) |
| GRT | St_Contable | I | Sí | Sí | Sí | Fis+, Trans− en destino (confirma GIB) |
| GET | St_Contable | I | Sí | Sí | Sí | Traslado entre bodegas (egreso) |
| GME | St_DevVen | C | Sí | Sí | Sí | Fis− (despacho físico final) |
| GRC | St_DevCom | P | Sí | Sí | No | Devolución compra: Disp+, Fis+ |
| NCE | St_Contable | C | Sí | No | No | Nota crédito electrónica: Disp+ |
| NVM | St_Pedido | C | No | Sí | No | Nota venta mayorista: Disp− (pedido) |
| VMN | St_Pedido | C | Sí | Sí | No | Venta mayorista: Disp− |
| Gdc | St_DevCom/St_Consignado | P/C | Sí | Sí | Mixto | Consignación |

## Lógica de reconstrucción de Físico

```
TIPOOPERACION=I + ESTRANSITORIO=False → Fis+
TIPOOPERACION=I + ESTRANSITORIO=True  → Trans+ (GIB); espera GRT
GRT (confirma GIB)                    → Fis+, Trans−
TIPOOPERACION=C + ESDESPACHO=True     → Fis−  (GME)
TIPOOPERACION=C + ESDESPACHO=False    → Disp− únicamente (BVE/FVE)
```

## Línea de detalle: ¿qué bodega registra cada doc?

- **GIB**: `IDBODEGA` en detalle = bodega de **origen** (la que envía)
- **GRT**: `IDBODEGA` en detalle = bodega de **destino** (la que recibe y confirma)
- **GME**: `IDBODEGA` en detalle = bodega que **despacha** (físico sale de ahí)
- **BVE/FVE**: `IDBODEGA` en detalle = bodega de **venta**

## Ciclo Calzada (stock negativo permitido, bod=44 CSV)

1. BVE/FVE → Disp− (puede quedar negativo)
2. GRT (llegada del producto) → Disp↑ a 0, Fis+ al total recibido
3. GME → Fis− (cierra físico, Dif=0)

Diferencia positiva (Disp=0, Fis>0) entre GRT y GME es **estado normal**, no error.
