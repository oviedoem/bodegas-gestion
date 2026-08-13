@echo off
echo === DESCARGANDO BODEGAS IR desde ERP ===
E:\python-portable\python.exe scripts\descargar_stock_erp.py IR
if errorlevel 1 ( echo ERROR en descarga IR & pause & exit /b 1 )
echo.
echo Listo. Revisar data\bodegas_IR.json
pause
