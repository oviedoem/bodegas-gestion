---
description: Guía paso a paso para regenerar los JSONs y HTML de merma de Isabel Riquelme tras actualizar MERMA.xlsx. Verifica prerequisitos, ejecuta scripts en orden y confirma resultado.
---

Eres el agente de regeneración de merma para Sucursal Isabel Riquelme.

## Prerequisitos (verificar antes de ejecutar)
1. `MERMA.xlsx` actualizado en `E:\BODEGAS GESTION\`
2. VPN FortiClient activa (para conexión SQL Server Foviedo)
3. Python portable disponible: `E:\python-portable\python.exe`

## Verificación previa
```powershell
# Ver fecha de MERMA.xlsx
(Get-Item "E:\BODEGAS GESTION\MERMA.xlsx").LastWriteTime

# Ver fecha del JSON actual
(Get-Item "E:\BODEGAS GESTION\merma_isabel_riquelme.json").LastWriteTime
```

## Ejecución en orden

### Paso 1 — Merma principal (bodega MIR=75)
```
E:\python-portable\python.exe "E:\BODEGAS GESTION\generar_merma_ir.py"
```
Genera: `merma_isabel_riquelme.json` + `MERMA_ISABEL_RIQUELME.html` + `index.html`

### Paso 2 — Otras bodegas (CAL, SER, WEB, GO, GAR, IIR, BMC, RST, HEL)
```
E:\python-portable\python.exe "E:\BODEGAS GESTION\generar_bodegas_ir.py"
```
Genera: `bodegas_ir_otras.json` (corre en lotes de 2 bodegas)

### Paso 3 — Deploy y commit
```
ACTUALIZAR_MERMA_IR.bat
```

## Verificación post-ejecución
- Confirmar que los JSON tienen fecha de hoy
- Confirmar que `index.html` fue actualizado
- Revisar que no aparecen errores de conexión SQL en la salida

## Reglas
- SOLO editar dentro de `E:\BODEGAS GESTION\`
- NO copiar credenciales SQL a ningún archivo aquí
- Si falla la conexión SQL → verificar VPN primero
- SUCURSAL_ID = '02' · BODEGA_MERMA = 75 (MIR)
