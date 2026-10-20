@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
title VIM ERP - Reiniciar datos

echo ============================================================
echo    VIM ERP - Volver al estado de instalacion nueva
echo ============================================================
echo.
echo Esto BORRA la base de datos: ventas, productos, usuarios,
echo caja, compras y configuracion. No se puede deshacer.
echo.
echo Antes de borrar se guarda una copia de seguridad por las dudas.
echo.
echo IMPORTANTE: cerra el programa antes de continuar.
echo.
echo    1 = Base del codigo fuente  (la que usa run.bat)
echo    2 = Base del ejecutable     (la que usa VIM_ERP.exe)
echo    3 = Las dos
echo    0 = Cancelar
echo.

set "OPCION="
set /p "OPCION=Cual queres reiniciar? "

if "%OPCION%"=="0" goto :cancelado
if "%OPCION%"=="" goto :cancelado
if "%OPCION%"=="1" goto :confirmar
if "%OPCION%"=="2" goto :confirmar
if "%OPCION%"=="3" goto :confirmar
echo.
echo Opcion no valida.
goto :fin

:confirmar
echo.
echo Escribi BORRAR (en mayusculas) para confirmar.
set "RESPUESTA="
set /p "RESPUESTA=Confirmacion: "
if not "%RESPUESTA%"=="BORRAR" goto :cancelado

rem Marca de tiempo para la copia de seguridad
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "STAMP=%%i"

if "%OPCION%"=="1" call :reiniciar "%~dp0database" "codigo fuente"
if "%OPCION%"=="2" call :reiniciar "%LOCALAPPDATA%\VIM_ERP\database" "ejecutable"
if "%OPCION%"=="3" (
    call :reiniciar "%~dp0database" "codigo fuente"
    call :reiniciar "%LOCALAPPDATA%\VIM_ERP\database" "ejecutable"
)

echo.
echo ============================================================
echo    LISTO
echo ============================================================
echo.
echo Al abrir el programa vas a encontrar:
echo    - Usuario: admin   Contrasena: 1234
echo    - Los 10 productos de ejemplo
echo    - La pregunta de que tipo de negocio es
echo.
goto :fin

:reiniciar
set "CARPETA=%~1"
set "ETIQUETA=%~2"
echo.
echo --- Base del %ETIQUETA% ---
echo     %CARPETA%

if not exist "%CARPETA%\vim_erp.db" (
    echo     No hay base ahi. Nada que borrar.
    exit /b 0
)

set "COPIA=%CARPETA%\reinicio_%STAMP%_vim_erp.db"
copy /y "%CARPETA%\vim_erp.db" "%COPIA%" >nul
if errorlevel 1 (
    echo     ERROR: no se pudo copiar. Esta el programa abierto?
    exit /b 1
)
echo     Copia guardada: reinicio_%STAMP%_vim_erp.db

del /q "%CARPETA%\vim_erp.db" 2>nul
if exist "%CARPETA%\vim_erp.db" (
    echo     ERROR: no se pudo borrar. Cerra el programa y proba de nuevo.
    exit /b 1
)

rem Archivos auxiliares de SQLite (modo WAL). Si quedan, la base
rem se puede reconstruir sola con datos viejos.
del /q "%CARPETA%\vim_erp.db-wal" 2>nul
del /q "%CARPETA%\vim_erp.db-shm" 2>nul
del /q "%CARPETA%\vim_erp.db-journal" 2>nul

echo     Base borrada. Se va a crear una nueva al abrir el programa.
exit /b 0

:cancelado
echo.
echo Cancelado. No se toco nada.

:fin
echo.
pause
