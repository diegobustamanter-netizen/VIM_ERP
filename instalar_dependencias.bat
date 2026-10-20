@echo off
chcp 65001 >nul
setlocal

echo ============================================================
echo    VIM ERP - Instalacion de dependencias
echo ============================================================
echo.

set "PYEXE=C:\Users\Diego\AppData\Local\Programs\Python\Python314\python.exe"
set "REQS=%~dp0requirements.txt"

if not exist "%PYEXE%" (
    echo No se encontro Python en la ruta esperada:
    echo    %PYEXE%
    echo Se probara con el Python del PATH.
    echo.
    set "PYEXE=python"
)

if not exist "%REQS%" (
    echo ERROR: no se encontro requirements.txt junto a este archivo.
    echo Este .bat debe quedar dentro de la carpeta VIM_ERP.
    goto :fin
)

echo Python   : %PYEXE%
echo Paquetes : %REQS%
echo.

echo [1/3] Verificando pip...
"%PYEXE%" -m pip --version >nul 2>&1
if errorlevel 1 (
    echo    pip no esta disponible, instalandolo...
    "%PYEXE%" -m ensurepip --upgrade
)

echo [2/3] Actualizando pip...
"%PYEXE%" -m pip install --upgrade pip

echo.
echo [3/3] Instalando las librerias del programa...
echo    (tkcalendar, Pillow, matplotlib, openpyxl, python-docx)
echo.
"%PYEXE%" -m pip install -r "%REQS%"

if errorlevel 1 (
    echo.
    echo ============================================================
    echo    ALGO FALLO
    echo    Copia el texto de arriba y pasaselo a Claude.
    echo ============================================================
) else (
    echo.
    echo ============================================================
    echo    LISTO - ya podes abrir el programa
    echo ============================================================
)

:fin
echo.
pause
