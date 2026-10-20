@echo off
chcp 65001 >nul
title VIM ERP - Pruebas
cd /d "%~dp0tests"

set "PYEXE=C:\Users\Diego\AppData\Local\Programs\Python\Python314\python.exe"
if not exist "%PYEXE%" set "PYEXE=python"

echo ============================================================
echo    VIM ERP - Pruebas automaticas
echo ============================================================
echo.
echo Las pruebas usan una base temporal. Tu base real NO se toca.
echo.

"%PYEXE%" -m unittest discover -s . -p "test_*.py" -v
set "CODIGO=%ERRORLEVEL%"

echo.
if "%CODIGO%"=="0" (
    echo ============================================================
    echo    TODO OK - no se rompio nada
    echo ============================================================
) else (
    echo ============================================================
    echo    HAY PRUEBAS FALLANDO
    echo ============================================================
    echo.
    echo Busca las lineas que dicen FAIL o ERROR mas arriba.
    echo Cada prueba explica que estaba cuidando.
)

echo.
pause
exit /b %CODIGO%
