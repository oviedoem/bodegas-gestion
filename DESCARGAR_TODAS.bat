@echo off
echo === DESCARGA COMPLETA TODAS LAS SUCURSALES ===
echo Esto tarda ~15-20 min con pausas entre bodegas
echo.
echo --- IR ---
E:\python-portable\python.exe scripts\descargar_stock_erp.py IR
if errorlevel 1 ( echo ERROR en IR & pause & exit /b 1 )
echo Pausa 10s entre sucursales...
timeout /t 10 /nobreak > nul
echo.
echo --- EM ---
E:\python-portable\python.exe scripts\descargar_stock_erp.py EM
if errorlevel 1 ( echo ERROR en EM & pause & exit /b 1 )
echo Pausa 10s entre sucursales...
timeout /t 10 /nobreak > nul
echo.
echo --- SV ---
E:\python-portable\python.exe scripts\descargar_stock_erp.py SV
if errorlevel 1 ( echo ERROR en SV & pause & exit /b 1 )
echo Pausa 10s entre sucursales...
timeout /t 10 /nobreak > nul
echo.
echo --- LC ---
E:\python-portable\python.exe scripts\descargar_stock_erp.py LC
if errorlevel 1 ( echo ERROR en LC & pause & exit /b 1 )
echo Pausa 10s entre sucursales...
timeout /t 10 /nobreak > nul
echo.
echo --- LT ---
E:\python-portable\python.exe scripts\descargar_stock_erp.py LT
if errorlevel 1 ( echo ERROR en LT & pause & exit /b 1 )
echo Pausa 10s entre sucursales...
timeout /t 10 /nobreak > nul
echo.
echo --- Combinando ---
E:\python-portable\python.exe scripts\descargar_stock_erp.py COMBINAR
echo.
echo ===== FIN. bodegas_gestion.json actualizado =====
pause
