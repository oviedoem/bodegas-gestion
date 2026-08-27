@echo off
chcp 1252 >nul
setlocal

set BASE=E:\BODEGAS GESTION
set PYTHON=E:\python-portable\python.exe
set XLSM=%BASE%\datos-bodegas.xlsm
set VBS_CREAR=%BASE%\CREAR_BODEGAS_XLSM.vbs
set VBS_CORRER=%BASE%\correr_bodegas.vbs
set SCRIPT_JSON=%BASE%\xlsm_a_json_bodegas.py
set SCRIPT_GESTION=%BASE%\generar_bodegas_gestion.py
set SCRIPT_IR=%BASE%\generar_bodegas_ir.py
set LOG_DIR=%BASE%\logs

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

for /f "tokens=1-3 delims=/" %%a in ("%DATE%") do (
    set DIA=%%a
    set MES=%%b
    set ANO=%%c
)
set FECHA=%DIA%%MES%%ANO%
set LOG_XLSM=%LOG_DIR%\descarga_xlsm_%FECHA%.log

echo [%TIME%] ====== DESCARGAR_BODEGAS.bat ====== >> "%LOG_XLSM%"
echo [%TIME%] INICIO >> "%LOG_XLSM%"

:: ═══════════════════════════════════════════════════════════════════════
:: PASO A — Crear/actualizar datos-bodegas.xlsm si modBodegas.bas
::          es mas nuevo que el XLSM, o si el XLSM no existe
:: ═══════════════════════════════════════════════════════════════════════
echo [%TIME%] PASO A: verificando datos-bodegas.xlsm...

set NECESITA_CREAR=0
if not exist "%XLSM%" set NECESITA_CREAR=1

if "%NECESITA_CREAR%"=="1" (
    echo [%TIME%] PASO A: XLSM no existe. Creando...
    cscript //NoLogo "%VBS_CREAR%"
    if errorlevel 1 (
        echo [%TIME%] [ERROR] CREAR_BODEGAS_XLSM.vbs fallo. Abortando.
        goto FALLBACK
    )
    echo [%TIME%] [OK] datos-bodegas.xlsm creado.
) else (
    echo [%TIME%] PASO A: XLSM encontrado. OK.
)

:: ═══════════════════════════════════════════════════════════════════════
:: PASO B — Ejecutar BajarTodoBat macro en Excel (descarga via ADODB/SQL)
:: ═══════════════════════════════════════════════════════════════════════
echo [%TIME%] PASO B: ejecutando BajarTodoBat en datos-bodegas.xlsm...

:: Crear VBScript temporal para correr la macro
(
echo Dim xl, wb, flagLog
echo Set xl = CreateObject^("Excel.Application"^)
echo xl.Visible = False
echo xl.DisplayAlerts = False
echo Set wb = xl.Workbooks.Open^("%XLSM:\=\\%"^)
echo On Error Resume Next
echo xl.Run "modBodegas.BajarTodoBat"
echo If Err.Number ^<^> 0 Then
echo     WScript.Echo "[ERROR] Macro fallo: " ^& Err.Description
echo     wb.Close False: xl.Quit
echo     WScript.Quit 1
echo End If
echo On Error GoTo 0
echo wb.Save
echo wb.Close False
echo xl.Quit
echo WScript.Echo "[OK] BajarTodoBat completado."
) > "%VBS_CORRER%"

cscript //NoLogo "%VBS_CORRER%" >> "%LOG_XLSM%" 2>&1
if errorlevel 1 (
    echo [%TIME%] [ERROR] Macro XLSM fallo. Ver %LOG_XLSM%. Pasando a fallback Python.
    del /q "%VBS_CORRER%" 2>nul
    goto FALLBACK
)
del /q "%VBS_CORRER%" 2>nul
echo [%TIME%] [OK] PASO B completado. >> "%LOG_XLSM%"

:: ═══════════════════════════════════════════════════════════════════════
:: PASO C — Generar JSONs desde XLSM
:: ═══════════════════════════════════════════════════════════════════════
echo [%TIME%] PASO C: generando JSONs desde datos-bodegas.xlsm...
"%PYTHON%" "%SCRIPT_JSON%" >> "%LOG_XLSM%" 2>&1
if errorlevel 1 (
    echo [%TIME%] [ERROR] xlsm_a_json_bodegas.py fallo. Ver %LOG_XLSM%. Pasando a fallback Python.
    goto FALLBACK
)
echo [%TIME%] [OK] PASO C completado — JSONs generados desde XLSM. >> "%LOG_XLSM%"
goto DEPLOY

:: ═══════════════════════════════════════════════════════════════════════
:: FALLBACK — Usar scripts Python directos (segunda opcion)
:: ═══════════════════════════════════════════════════════════════════════
:FALLBACK
echo [%TIME%] *** FALLBACK: usando scripts Python directos ***
echo [%TIME%] FALLBACK activado >> "%LOG_XLSM%"

set LOG_FB=%LOG_DIR%\fallback_gestion_%FECHA%.log
set LOG_IR=%LOG_DIR%\fallback_ir_%FECHA%.log

echo [%TIME%] Corriendo generar_bodegas_gestion.py...
"%PYTHON%" "%SCRIPT_GESTION%" > "%LOG_FB%" 2>&1
if errorlevel 1 (
    echo [%TIME%] [ERROR] generar_bodegas_gestion.py fallo. Ver %LOG_FB%.
    echo [ERROR] FALLBACK generar_bodegas_gestion.py fallo >> "%LOG_XLSM%"
    goto FIN_ERROR
)
echo [%TIME%] [OK] generar_bodegas_gestion.py OK

echo [%TIME%] Corriendo generar_bodegas_ir.py...
"%PYTHON%" "%SCRIPT_IR%" > "%LOG_IR%" 2>&1
if errorlevel 1 (
    echo [%TIME%] [ERROR] generar_bodegas_ir.py fallo. Ver %LOG_IR%.
    echo [ERROR] FALLBACK generar_bodegas_ir.py fallo >> "%LOG_XLSM%"
    goto FIN_ERROR
)
echo [%TIME%] [OK] generar_bodegas_ir.py OK
echo [%TIME%] [OK] FALLBACK completado. >> "%LOG_XLSM%"

:: ═══════════════════════════════════════════════════════════════════════
:: DEPLOY — Copiar JSONs a git-sync y hacer firebase deploy hosting
:: ═══════════════════════════════════════════════════════════════════════
:DEPLOY
echo [%TIME%] PASO D: copiando JSONs a git-sync...

copy /Y "%BASE%\bodegas_gestion.json" "E:\git-sync\bodegas_gestion.json" >nul
if errorlevel 1 echo [AVISO] No se pudo copiar bodegas_gestion.json a git-sync

copy /Y "%BASE%\bodegas_ir_otras.json" "E:\git-sync\bodegas_ir_otras.json" >nul
if errorlevel 1 echo [AVISO] No se pudo copiar bodegas_ir_otras.json a git-sync

echo [%TIME%] [OK] Copias a git-sync completadas.
echo [%TIME%] PASO D completado >> "%LOG_XLSM%"

echo [%TIME%] ====== FIN OK ======
echo [%TIME%] FIN OK >> "%LOG_XLSM%"
goto FIN

:FIN_ERROR
echo [%TIME%] ====== FIN CON ERRORES ======
exit /b 1

:FIN
endlocal
