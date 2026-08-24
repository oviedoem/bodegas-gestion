@echo off
echo === DESCARGANDO BODEGAS SV desde ERP ===
E:\python-portable\python.exe scripts\descargar_stock_erp.py SV
if errorlevel 1 ( echo ERROR en descarga SV & pause & exit /b 1 )
echo.
echo Listo. Revisar data\bodegas_SV.json
pause
