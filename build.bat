@echo off
echo ============================================================
echo    VIM ERP - Build Profesional
echo ============================================================
echo.

echo [1/3] Generando icono multi-resolucion...
python crear_icono.py
if errorlevel 1 (
    echo ERROR: No se pudo crear el icono.
    pause
    exit /b 1
)
echo.

echo [2/3] Limpiando build anterior...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
echo    OK
echo.

echo [3/3] Compilando ejecutable con PyInstaller...
echo    Esto puede tardar varios minutos...
echo.
pyinstaller VIM_ERP.spec --clean --noconfirm
if errorlevel 1 (
    echo.
    echo ERROR: La compilacion fallo. Revise los errores arriba.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo    BUILD EXITOSO
echo ============================================================
echo.
echo    Ejecutable: dist\VIM_ERP.exe
echo.
for %%A in (dist\VIM_ERP.exe) do echo    Tamano: %%~zA bytes
echo.
echo    Para ejecutar: dist\VIM_ERP.exe
echo ============================================================
pause
