@echo off
echo === DESCARGANDO BODEGAS LT desde ERP ===
E:\python-portable\python.exe scripts\descargar_stock_erp.py LT
if errorlevel 1 ( echo ERROR en descarga LT & pause & exit /b 1 )
echo.
echo Listo. Revisar data\bodegas_LT.json
pause
