@echo off
chcp 65001 >nul
title VIM ERP
cd /d "%~dp0"

rem Python preferido: el que ya usas. Si no esta, se busca en el PATH.
set "PYEXE=C:\Users\Diego\AppData\Local\Programs\Python\Python314\python.exe"
if not exist "%PYEXE%" set "PYEXE=python"

if not exist "%~dp0ventana_principal.py" (
    echo.
    echo ERROR: no se encontro ventana_principal.py
    echo Este archivo debe quedar dentro de la carpeta VIM_ERP.
    echo.
    pause
    exit /b 1
)

echo Iniciando VIM ERP...
"%PYEXE%" "%~dp0ventana_principal.py"
set "CODIGO=%ERRORLEVEL%"

rem Si termino bien, la ventana se cierra sola. Si fallo, se queda
rem abierta para poder leer el error.
if not "%CODIGO%"=="0" (
    echo.
    echo ============================================================
    echo    EL PROGRAMA TERMINO CON UN ERROR  ^(codigo %CODIGO%^)
    echo ============================================================
    echo.
    echo Si arriba dice "ModuleNotFoundError", falta instalar
    echo alguna libreria: ejecuta instalar_dependencias.bat
    echo.
    echo Para cualquier otro error, copia el texto de arriba.
    echo.
    pause
)

exit /b %CODIGO%
