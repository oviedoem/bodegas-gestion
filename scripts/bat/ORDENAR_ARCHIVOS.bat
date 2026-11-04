@echo off
rem ORDENAR_ARCHIVOS.bat - informe por defecto; APLICAR mueve solo candidatos sin referencias.
setlocal
set PY=E:\python-portable\python.exe
cd /d "E:\BODEGAS GESTION"
if /i "%1"=="APLICAR" (
  "%PY%" scripts\ordenar_archivos.py --aplicar
) else if /i "%1"=="REVERTIR" (
  "%PY%" scripts\ordenar_archivos.py --revertir "%2"
) else (
  "%PY%" scripts\ordenar_archivos.py
  echo.
  echo Para aplicar: ORDENAR_ARCHIVOS.bat APLICAR
)
pause
endlocal
