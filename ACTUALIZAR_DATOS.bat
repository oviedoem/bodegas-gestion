@echo off
chcp 65001 >nul
setlocal

set PYTHON=E:\python-portable\python.exe
set PROJ=E:\BODEGAS GESTION

echo ============================================================
echo  BODEGAS GESTION — Actualizacion de datos frescos del ERP
echo  %DATE% %TIME%
echo ============================================================
echo.

:: Verificar que Python portable existe
if not exist "%PYTHON%" (
    echo ERROR: No se encuentra Python portable en:
    echo   %PYTHON%
    echo.
    echo Verifica que la ruta sea correcta.
    goto :FIN_ERROR
)
echo Python OK: %PYTHON%
echo Proyecto:  %PROJ%
echo.
pause

cd /d "%PROJ%"

:: ============================================================
:: PASO 1 — Merma Isabel Riquelme
:: ============================================================
echo [1/5] Merma IR ^(generar_merma_ir.py^)...
"%PYTHON%" "%PROJ%\generar_merma_ir.py"
if errorlevel 1 (
    echo.
    echo ERROR en generar_merma_ir.py ^(errorlevel=%ERRORLEVEL%^)
    goto :FIN_ERROR
)
echo    OK — merma_isabel_riquelme.json + MERMA_ISABEL_RIQUELME.html
echo.

:: ============================================================
:: PASO 2 — Bodegas todas las sucursales
:: ============================================================
echo [2/5] Bodegas SQL ^(scripts\descargar_bodegas_sql.py^)...
echo NOTA: si alguna sucursal sale en 0, espera 5-10 min y repite este paso.
"%PYTHON%" "%PROJ%\scripts\descargar_bodegas_sql.py"
if errorlevel 1 (
    echo.
    echo ERROR en descargar_bodegas_sql.py ^(errorlevel=%ERRORLEVEL%^)
    goto :FIN_ERROR
)
echo    OK — bodegas_gestion.json + bodegas_ir_otras.json
echo.

:: ============================================================
:: PASO 3 — Diferencias bodegas San Vicente
:: ============================================================
echo [3/5] Diferencias SV ^(scripts\descargar_dif_sv.py^)...
"%PYTHON%" "%PROJ%\scripts\descargar_dif_sv.py"
if errorlevel 1 (
    echo.
    echo ERROR en descargar_dif_sv.py ^(errorlevel=%ERRORLEVEL%^)
    goto :FIN_ERROR
)
echo    OK — data\dif-bodegas-sv.json
echo.

:: ============================================================
:: PASO 4 — Stock critico Las Cabras
:: ============================================================
echo [4/5] Stock critico LC ^(scripts\descargar_stock_critico_lc.py^)...
"%PYTHON%" "%PROJ%\scripts\descargar_stock_critico_lc.py"
if errorlevel 1 (
    echo.
    echo ERROR en descargar_stock_critico_lc.py ^(errorlevel=%ERRORLEVEL%^)
    goto :FIN_ERROR
)
echo    OK — data\stock-critico-lc.json
echo.

:: ============================================================
:: PASO 5 — OC pendientes Las Cabras
:: ============================================================
echo [5/5] OC pendientes LC ^(scripts\descargar_oc_pendientes_lc.py^)...
"%PYTHON%" "%PROJ%\scripts\descargar_oc_pendientes_lc.py"
if errorlevel 1 (
    echo.
    echo ERROR en descargar_oc_pendientes_lc.py ^(errorlevel=%ERRORLEVEL%^)
    goto :FIN_ERROR
)
echo    OK — data\oc-pend-resumen-lc.json
echo.

:: ============================================================
:: EXITO
:: ============================================================
echo ============================================================
echo  DESCARGA COMPLETA — archivos generados:
echo.
echo    bodegas_gestion.json
echo    bodegas_ir_otras.json
echo    data\dif-bodegas-sv.json
echo    data\stock-critico-lc.json
echo    data\oc-pend-resumen-lc.json
echo    merma_isabel_riquelme.json
echo    MERMA_ISABEL_RIQUELME.html
echo.
echo  Para publicar (en terminal):
echo    git add bodegas_gestion.json bodegas_ir_otras.json
echo    git add data\dif-bodegas-sv.json data\stock-critico-lc.json data\oc-pend-resumen-lc.json
echo    git add merma_isabel_riquelme.json MERMA_ISABEL_RIQUELME.html
echo    git commit -m "data: datos frescos %DATE%"
echo    git push
echo ============================================================
goto :FIN_OK

:FIN_ERROR
echo.
echo ============================================================
echo  PROCESO ABORTADO — revisa el error arriba.
echo  Si es error SQL: verifica que la VPN este activa.
echo  Si es error de modulo Python: revisa que pyodbc este instalado.
echo ============================================================

:FIN_OK
echo.
pause
