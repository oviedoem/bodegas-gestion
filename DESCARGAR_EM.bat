@echo off
echo === DESCARGANDO BODEGAS EM desde ERP ===
E:\python-portable\python.exe scripts\descargar_stock_erp.py EM
if errorlevel 1 ( echo ERROR en descarga EM & pause & exit /b 1 )
echo.
echo Listo. Revisar data\bodegas_EM.json
pause
