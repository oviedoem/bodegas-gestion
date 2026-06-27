@echo off
chcp 1252 >nul
title MERMA ISABEL RIQUELME - Actualizacion de datos
cd /d "%~dp0"
color 0A
cls

:: ============================================================
:: RESOLVER PYTHON PORTABLE (E: con fallback a PATH)
:: ============================================================
if exist "E:\python-portable\python.exe" (
    set PYTHON_EXE=E:\python-portable\python.exe
) else (
    set PYTHON_EXE=python
)

echo.
echo  ============================================================
echo   MERMA SUCURSAL ISABEL RIQUELME - Actualizacion de datos
echo   SQL Server (solo lectura) + MERMA.xlsx -^> Reporte HTML
echo  ============================================================
echo.

echo  [CHECK] Python...
"%PYTHON_EXE%" --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo.
    echo  [ERROR] Python no esta instalado o no esta en el PATH.
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('"%PYTHON_EXE%" --version 2^>^&1') do echo         %%v

echo  [CHECK] MERMA.xlsx...
if not exist "%~dp0MERMA.xlsx" (
    color 0C
    echo  [ERROR] No se encontro MERMA.xlsx en esta carpeta.
    pause
    exit /b 1
)
echo         OK

echo  [CHECK] generar_merma_ir.py...
if not exist "%~dp0generar_merma_ir.py" (
    color 0C
    echo  [ERROR] No se encontro generar_merma_ir.py
    pause
    exit /b 1
)
echo         OK

echo.
timeout /t 2 /nobreak >nul

echo.
echo  +----------------------------------------------------------+
echo  ^|  Descargando movimientos bodega MIR desde SQL Server  ^|
echo  +----------------------------------------------------------+
echo.

"%PYTHON_EXE%" "%~dp0generar_merma_ir.py"
if %errorlevel% neq 0 (
    color 0C
    echo.
    echo  [ERROR] generar_merma_ir.py fallo. Revisar VPN/conexion SQL Server.
    echo  (Si fue la regla anti-retroceso, el reporte anterior se mantuvo intacto.)
    echo.
    pause
    exit /b 1
)

color 0A
echo.
echo  ============================================================
echo   ACTUALIZACION COMPLETA
echo   [OK] merma_isabel_riquelme.json
echo   [OK] MERMA_ISABEL_RIQUELME.html
echo  ============================================================
echo.
echo  Abriendo reporte...
start "" "%~dp0MERMA_ISABEL_RIQUELME.html"
echo.
pause
