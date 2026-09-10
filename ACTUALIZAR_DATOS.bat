@echo off
setlocal

set PYTHON=E:\python-portable\python.exe
set PROJ=E:\BODEGAS GESTION

echo ============================================================
echo  BODEGAS GESTION - Actualizacion de datos frescos del ERP
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
:: PASO 1 - Merma Isabel Riquelme
:: ============================================================
echo [1/7] Merma IR (generar_merma_ir.py)...
"%PYTHON%" "%PROJ%\generar_merma_ir.py"
if errorlevel 1 (
    echo.
    echo ERROR en generar_merma_ir.py
    goto :FIN_ERROR
)
echo    OK - merma_isabel_riquelme.json + MERMA_ISABEL_RIQUELME.html
echo.

:: ============================================================
:: PASO 2 - Bodegas todas las sucursales
:: ============================================================
echo [2/7] Bodegas SQL (scripts\descargar_bodegas_sql.py)...
echo NOTA: si alguna sucursal sale en 0, espera 5-10 min y repite.
"%PYTHON%" "%PROJ%\scripts\descargar_bodegas_sql.py"
if errorlevel 1 (
    echo.
    echo ERROR en descargar_bodegas_sql.py
    goto :FIN_ERROR
)
echo    OK - bodegas_gestion.json + bodegas_ir_otras.json
echo.

:: ============================================================
:: PASO 3 - Recortes por modo de usuario (SV/LC) desde bodegas_gestion.json
:: ============================================================
echo [3/7] Recorte SV/LC (scripts\generar_bodegas_modo.py)...
echo NOTA: no baja nada nuevo del ERP, solo recorta bodegas_gestion.json ya
echo       descargado. Debe ir SIEMPRE despues del paso 2, nunca antes.
"%PYTHON%" "%PROJ%\scripts\generar_bodegas_modo.py"
if errorlevel 1 (
    echo.
    echo ERROR en generar_bodegas_modo.py
    goto :FIN_ERROR
)
echo    OK - data\bodegas-sv.json + data\bodegas-lc.json
echo.

:: ============================================================
:: PASO 4 - Diferencias bodegas San Vicente
:: ============================================================
echo [4/7] Diferencias SV (scripts\descargar_dif_sv.py)...
"%PYTHON%" "%PROJ%\scripts\descargar_dif_sv.py"
if errorlevel 1 (
    echo.
    echo ERROR en descargar_dif_sv.py
    goto :FIN_ERROR
)
echo    OK - data\dif-bodegas-sv.json
echo.

:: ============================================================
:: PASO 5 - Stock critico Las Cabras
:: ============================================================
echo [5/7] Stock critico LC (scripts\descargar_stock_critico_lc.py)...
"%PYTHON%" "%PROJ%\scripts\descargar_stock_critico_lc.py"
if errorlevel 1 (
    echo.
    echo ERROR en descargar_stock_critico_lc.py
    goto :FIN_ERROR
)
echo    OK - data\stock-critico-lc.json
echo.

:: ============================================================
:: PASO 6 - OC pendientes Las Cabras
:: ============================================================
echo [6/7] OC pendientes LC (scripts\descargar_oc_pendientes_lc.py)...
"%PYTHON%" "%PROJ%\scripts\descargar_oc_pendientes_lc.py"
if errorlevel 1 (
    echo.
    echo ERROR en descargar_oc_pendientes_lc.py
    goto :FIN_ERROR
)
echo    OK - data\oc-pend-resumen-lc.json
echo.

:: ============================================================
:: PASO 7 - Consumo Interno (Guia de Consumo, todas las sucursales)
:: ============================================================
echo [7/7] Consumo Interno (scripts\descargar_consumo_interno.py)...
"%PYTHON%" "%PROJ%\scripts\descargar_consumo_interno.py"
if errorlevel 1 (
    echo.
    echo ERROR en descargar_consumo_interno.py
    goto :FIN_ERROR
)
echo    OK - data\consumo-interno.json
echo.

:: ============================================================
:: EXITO
:: ============================================================
echo ============================================================
echo  DESCARGA COMPLETA - archivos generados:
echo.
echo    bodegas_gestion.json
echo    bodegas_ir_otras.json
echo    data\bodegas-sv.json + data\bodegas-lc.json (recorte MODO_SV/MODO_LC)
echo    data\dif-bodegas-sv.json
echo    data\stock-critico-lc.json
echo    data\oc-pend-resumen-lc.json
echo    data\consumo-interno.json
echo    merma_isabel_riquelme.json
echo    MERMA_ISABEL_RIQUELME.html
echo ============================================================
echo.

set /p PUBLICAR="Publicar ahora (git commit+push y deploy Firebase)? [S/N]: "
if /i not "%PUBLICAR%"=="S" (
    echo.
    echo  Sin publicar. Los archivos quedan listos en disco; para publicar despues:
    echo    git add bodegas_gestion.json bodegas_ir_otras.json
    echo    git add data\bodegas-sv.json data\bodegas-lc.json
    echo    git add data\dif-bodegas-sv.json data\stock-critico-lc.json data\oc-pend-resumen-lc.json
    echo    git add data\consumo-interno.json
    echo    git add merma_isabel_riquelme.json MERMA_ISABEL_RIQUELME.html
    echo    git commit -m "data: datos frescos"  ^&^& git push
    echo    E:\npm-global\firebase.cmd deploy --only hosting --project isabel-riquelme-merma
    goto :FIN_OK
)

echo.
echo [PUBLICAR 1/3] git add + commit...
git add bodegas_gestion.json bodegas_ir_otras.json
git add data\bodegas-sv.json data\bodegas-lc.json
git add data\dif-bodegas-sv.json data\stock-critico-lc.json data\oc-pend-resumen-lc.json
git add data\consumo-interno.json
git add merma_isabel_riquelme.json MERMA_ISABEL_RIQUELME.html
git commit -m "data: datos frescos %DATE%"
if errorlevel 1 (
    echo  [INFO] Nada nuevo para comitear o el commit fallo - revisa arriba.
)

echo.
echo [PUBLICAR 2/3] git push...
git push
if errorlevel 1 (
    echo.
    echo  [ERROR] git push fallo. Revisa conexion/credenciales de git.
    goto :FIN_ERROR
)

echo.
echo [PUBLICAR 3/3] Deploy Firebase Hosting...
call "%PROJ%\DEPLOY_APP.bat"

echo.
echo ============================================================
echo  PUBLICADO - isabel-riquelme-merma.web.app
echo ============================================================
goto :FIN_OK

:FIN_ERROR
echo.
echo ============================================================
echo  PROCESO ABORTADO - revisa el error arriba.
echo  Si es error SQL: verifica que la VPN este activa.
echo  Si es error de modulo: revisa que pyodbc este instalado.
echo ============================================================

:FIN_OK
echo.
pause
