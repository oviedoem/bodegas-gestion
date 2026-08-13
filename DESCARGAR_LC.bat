@echo off
echo === DESCARGANDO BODEGAS LC desde ERP ===
E:\python-portable\python.exe scripts\descargar_stock_erp.py LC
if errorlevel 1 ( echo ERROR en descarga LC & pause & exit /b 1 )
echo.
echo Listo. Revisar data\bodegas_LC.json
pause
