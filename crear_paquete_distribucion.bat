@echo off
setlocal
title VIM ERP - Crear paquete

REM ------------------------------------------------------------
REM  IMPORTANTE: este archivo debe mantenerse en ASCII puro.
REM  Sin tildes, sin enies y sin caracteres de dibujo tipo cuadro.
REM  cmd.exe los interpreta mal y rompe el parseo de todo el .bat
REM  (las variables terminan vacias y salen errores sin sentido).
REM ------------------------------------------------------------

set "BUILD_WORKPATH=%TEMP%\VIM_ERP_build_%RANDOM%_%RANDOM%"
set "OUT_DIR=..\dist_para_enviar"
set "ZIP_FILE=..\VIM_ERP_Windows.zip"
set "LOG_TESTS=%TEMP%\vimerp_tests.log"

echo ============================================================
echo    VIM ERP - Paquete de distribucion Windows
echo ============================================================
echo.
echo    Salida: %OUT_DIR%
echo    ZIP:    %ZIP_FILE%
echo.

REM --- [1/5] Pruebas automaticas -------------------------------
REM Empaquetar codigo roto significa perder el viaje al otro PC.
echo [1/5] Corriendo las pruebas automaticas...
pushd tests
python -m unittest discover -s . -p "test_*.py" > "%LOG_TESTS%" 2>&1
set "TESTS_FALLARON=%ERRORLEVEL%"
popd

if not "%TESTS_FALLARON%"=="0" (
    echo.
    echo ============================================================
    echo    HAY PRUEBAS FALLANDO - NO SE GENERA EL PAQUETE
    echo ============================================================
    echo.
    findstr /C:"FAIL" /C:"ERROR" /C:"Ran " "%LOG_TESTS%"
    echo.
    echo    Detalle completo: %LOG_TESTS%
    echo    Corrige lo que falla y vuelve a intentar.
    echo.
    goto :limpiar_y_salir
)
findstr /C:"Ran " "%LOG_TESTS%"
echo    Todas las pruebas pasaron.
echo.

REM --- [2/5] Icono ---------------------------------------------
echo [2/5] Generando icono...
python crear_icono.py
if errorlevel 1 (
    echo ERROR: No se pudo generar el icono.
    goto :limpiar_y_salir
)
echo.

REM --- [3/5] Compilar ------------------------------------------
echo [3/5] Compilando ejecutable...
echo    Carpeta temporal de build: %BUILD_WORKPATH%
pyinstaller VIM_ERP.spec --clean --noconfirm --workpath "%BUILD_WORKPATH%"
if errorlevel 1 (
    echo ERROR: La compilacion fallo.
    goto :limpiar_y_salir
)

if not exist "dist\VIM_ERP.exe" (
    echo.
    echo ERROR: PyInstaller termino pero no se encontro dist\VIM_ERP.exe
    goto :limpiar_y_salir
)
echo.

REM --- [4/5] Armar la carpeta ----------------------------------
echo [4/5] Preparando carpeta para enviar...

REM Sello de version: en otro PC esto dice que build se esta probando.
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HHmm"') do set "SELLO=%%i"
if not defined SELLO set "SELLO=sin-fecha"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ErrorActionPreference='Stop';" ^
    "try {" ^
    "  $out='%OUT_DIR%';" ^
    "  if (Test-Path $out) { Remove-Item $out -Recurse -Force };" ^
    "  New-Item -ItemType Directory -Path $out -Force | Out-Null;" ^
    "  Copy-Item 'dist\VIM_ERP.exe' (Join-Path $out 'VIM_ERP.exe') -Force;" ^
    "  Copy-Item 'LEEME_DISTRIBUCION.txt' (Join-Path $out 'LEEME_DISTRIBUCION.txt') -Force;" ^
    "  $manual = $null;" ^
    "  foreach ($ruta in @('Manual_de_Uso_VIM_ERP.docx','..\Manual_de_Uso_VIM_ERP.docx')) {" ^
    "    if (Test-Path $ruta) { $manual = $ruta; break }" ^
    "  };" ^
    "  if ($manual) { Copy-Item $manual (Join-Path $out 'Manual_de_Uso_VIM_ERP.docx') -Force; Write-Host ('   Manual incluido desde: ' + $manual) }" ^
    "  else { Write-Host '   AVISO: no se encontro el manual. Puedes generarlo con: python generar_manual_usuario.py' };" ^
    "  $tam = [math]::Round((Get-Item 'dist\VIM_ERP.exe').Length / 1MB, 1);" ^
    "  Write-Host ('   Ejecutable: ' + $tam + ' MB');" ^
    "  exit 0" ^
    "} catch { Write-Host ('ERROR: ' + $_.Exception.Message); exit 1 }"

if errorlevel 1 (
    echo ERROR: No se pudo preparar la carpeta de envio.
    goto :limpiar_y_salir
)

if not exist "%OUT_DIR%\VIM_ERP.exe" (
    echo ERROR: No se copio el ejecutable a la carpeta de envio.
    goto :limpiar_y_salir
)

REM VERSION.txt se escribe con echo comun, no con PowerShell:
REM las comillas escapadas dentro de -Command dan mas problemas.
set "ARCH_VER=%OUT_DIR%\VERSION.txt"
echo VIM ERP> "%ARCH_VER%"
echo.>> "%ARCH_VER%"
echo Build: %SELLO%>> "%ARCH_VER%"
echo.>> "%ARCH_VER%"
echo Si estas probando en otro equipo, revisa que esta fecha>> "%ARCH_VER%"
echo coincida con la del build que querias probar.>> "%ARCH_VER%"
echo.>> "%ARCH_VER%"
echo Este paquete se genero con todas las pruebas automaticas>> "%ARCH_VER%"
echo en verde.>> "%ARCH_VER%"
echo    VERSION.txt creado (build %SELLO%)
echo.

REM --- [5/5] ZIP -----------------------------------------------
echo [5/5] Creando ZIP...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ErrorActionPreference='Stop';" ^
    "try {" ^
    "  $zip='%ZIP_FILE%';" ^
    "  if (Test-Path $zip) { Remove-Item $zip -Force };" ^
    "  Compress-Archive -Path '%OUT_DIR%\*' -DestinationPath $zip -Force;" ^
    "  $mb = [math]::Round((Get-Item $zip).Length / 1MB, 1);" ^
    "  Write-Host ('   ZIP: ' + $mb + ' MB');" ^
    "  exit 0" ^
    "} catch { Write-Host ('ERROR: ' + $_.Exception.Message); exit 1 }"

if errorlevel 1 (
    echo ERROR: No se pudo crear el ZIP.
    goto :limpiar_y_salir
)

echo.
echo ============================================================
echo    PAQUETE LISTO  -  Build %SELLO%
echo ============================================================
echo.
echo    Enviar:  %ZIP_FILE%
echo    Carpeta: %OUT_DIR%
echo.
echo    Contenido:
echo       VIM_ERP.exe
echo       LEEME_DISTRIBUCION.txt
echo       Manual_de_Uso_VIM_ERP.docx
echo       VERSION.txt  (build %SELLO%)
echo.
echo    En el otro PC: abre VERSION.txt para confirmar
echo    que estas probando el build correcto.
echo.

:limpiar_y_salir
echo.
echo Limpiando carpeta temporal de build...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$p='%BUILD_WORKPATH%';" ^
    "if ($p -and (Test-Path -LiteralPath $p)) { Remove-Item -LiteralPath $p -Recurse -Force -ErrorAction SilentlyContinue; Write-Host '   Temp eliminado.' } else { Write-Host '   Sin temp que limpiar.' }"
pause
