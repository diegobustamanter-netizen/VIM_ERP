@echo off
setlocal
title VIM ERP - Crear paquete para publicar
cd /d "%~dp0"

REM ------------------------------------------------------------
REM  IMPORTANTE: este archivo debe mantenerse en ASCII puro y con
REM  saltos de linea de Windows (CRLF). Sin tildes ni enies:
REM  cmd.exe los interpreta mal y rompe el parseo de todo el .bat.
REM ------------------------------------------------------------

REM Version que se publica. Cambiala aqui en cada version nueva.
set "VERSION=1.0"

set "NOMBRE=VIM_ERP_v%VERSION%_Windows"
set "OUT_DIR=..\%NOMBRE%"
set "ZIP_FILE=..\%NOMBRE%.zip"
set "BUILD_WORKPATH=%TEMP%\VIM_ERP_build_%RANDOM%_%RANDOM%"
set "LOG_TESTS=%TEMP%\vimerp_tests.log"

set "PYEXE=C:\Users\Diego\AppData\Local\Programs\Python\Python314\python.exe"
if not exist "%PYEXE%" set "PYEXE=python"

echo ============================================================
echo    VIM ERP %VERSION% - Paquete para publicar
echo ============================================================
echo.
echo    Carpeta: %OUT_DIR%
echo    ZIP:     %ZIP_FILE%
echo.

REM --- [1/6] Pruebas automaticas -------------------------------
REM Publicar codigo roto es lo peor que puede pasar: se corre todo antes.
echo [1/6] Corriendo las pruebas automaticas...
pushd tests
"%PYEXE%" -m unittest discover -s . -p "test_*.py" > "%LOG_TESTS%" 2>&1
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
    goto :limpiar_y_salir
)
findstr /C:"Ran " "%LOG_TESTS%"
echo    Todas las pruebas pasaron.
echo.

REM --- [2/6] Icono ---------------------------------------------
echo [2/6] Generando icono...
"%PYEXE%" crear_icono.py
if errorlevel 1 (
    echo ERROR: No se pudo generar el icono.
    goto :limpiar_y_salir
)
echo.

REM --- [3/6] Compilar ------------------------------------------
echo [3/6] Compilando el ejecutable (tarda varios minutos)...
if exist "dist\VIM_ERP.exe" del /q "dist\VIM_ERP.exe"
"%PYEXE%" -m PyInstaller VIM_ERP.spec --clean --noconfirm --workpath "%BUILD_WORKPATH%"
if errorlevel 1 (
    echo ERROR: La compilacion fallo.
    goto :limpiar_y_salir
)
if not exist "dist\VIM_ERP.exe" (
    echo ERROR: PyInstaller termino pero no se encontro dist\VIM_ERP.exe
    goto :limpiar_y_salir
)
echo.

REM --- [4/6] Manual --------------------------------------------
REM Se usa el manual del escritorio (..\) si existe, porque ahi es donde
REM se pegan las capturas. Si no, se genera uno nuevo sin capturas.
echo [4/6] Buscando el manual...
set "MANUAL=..\Manual_de_Uso_VIM_ERP.docx"
if not exist "%MANUAL%" (
    echo    No hay manual en %MANUAL%: se genera uno nuevo, sin capturas.
    "%PYEXE%" generar_manual_usuario.py
    set "MANUAL=Manual_de_Uso_VIM_ERP.docx"
)
echo    Manual: %MANUAL%
echo.

REM --- [5/6] Armar la carpeta ----------------------------------
echo [5/6] Armando la carpeta para publicar...
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set "FECHA=%%i"
if not defined FECHA set "FECHA=sin-fecha"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ErrorActionPreference='Stop';" ^
    "try {" ^
    "  $out='%OUT_DIR%';" ^
    "  if (Test-Path $out) { Remove-Item $out -Recurse -Force };" ^
    "  New-Item -ItemType Directory -Path $out -Force | Out-Null;" ^
    "  Copy-Item 'dist\VIM_ERP.exe' (Join-Path $out 'VIM_ERP.exe') -Force;" ^
    "  Copy-Item 'LEEME_DISTRIBUCION.txt' (Join-Path $out 'LEEME.txt') -Force;" ^
    "  Copy-Item 'LICENSE' (Join-Path $out 'LICENCIA.txt') -Force;" ^
    "  $docx = Join-Path $out 'Manual_de_Uso_VIM_ERP.docx';" ^
    "  Copy-Item '%MANUAL%' $docx -Force;" ^
    "  try {" ^
    "    $word = New-Object -ComObject Word.Application; $word.Visible = $false;" ^
    "    $d = $word.Documents.Open((Resolve-Path $docx).Path, $false, $true);" ^
    "    $pdf = [IO.Path]::ChangeExtension((Resolve-Path $docx).Path, 'pdf');" ^
    "    $d.SaveAs([ref]$pdf, [ref]17); $d.Close(); $word.Quit();" ^
    "    Write-Host '   Manual tambien en PDF.'" ^
    "  } catch { Write-Host '   AVISO: sin Word instalado no se pudo crear el PDF del manual. Va solo el .docx.' };" ^
    "  $hash = (Get-FileHash (Join-Path $out 'VIM_ERP.exe') -Algorithm SHA256).Hash;" ^
    "  $tam = [math]::Round((Get-Item (Join-Path $out 'VIM_ERP.exe')).Length / 1MB, 1);" ^
    "  $ver = @('VIM ERP %VERSION%', '', 'Fecha de publicacion: %FECHA%', '', 'Huella SHA-256 de VIM_ERP.exe (para verificar que la descarga no fue alterada):', $hash, '', 'Paquete generado con todas las pruebas automaticas en verde.');" ^
    "  Set-Content -Path (Join-Path $out 'VERSION.txt') -Value $ver -Encoding ASCII;" ^
    "  Write-Host ('   Ejecutable: ' + $tam + ' MB');" ^
    "  exit 0" ^
    "} catch { Write-Host ('ERROR: ' + $_.Exception.Message); exit 1 }"
if errorlevel 1 (
    echo ERROR: No se pudo armar la carpeta.
    goto :limpiar_y_salir
)
echo.

REM --- [6/6] ZIP -----------------------------------------------
echo [6/6] Creando el ZIP...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ErrorActionPreference='Stop';" ^
    "try {" ^
    "  $zip='%ZIP_FILE%';" ^
    "  if (Test-Path $zip) { Remove-Item $zip -Force };" ^
    "  Compress-Archive -Path '%OUT_DIR%' -DestinationPath $zip -Force;" ^
    "  $hash = (Get-FileHash $zip -Algorithm SHA256).Hash;" ^
    "  Set-Content -Path ($zip + '.sha256.txt') -Value ($hash + '  %NOMBRE%.zip') -Encoding ASCII;" ^
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
echo    PAQUETE LISTO  -  VIM ERP %VERSION%
echo ============================================================
echo.
echo    Para subir a internet:  %ZIP_FILE%
echo    Huella del ZIP:         %ZIP_FILE%.sha256.txt
echo.
echo    Dentro del ZIP (carpeta %NOMBRE%):
echo       VIM_ERP.exe
echo       Manual_de_Uso_VIM_ERP.docx  (y .pdf si tienes Word)
echo       LEEME.txt
echo       LICENCIA.txt
echo       VERSION.txt
echo.

:limpiar_y_salir
echo.
echo Limpiando archivos temporales de la compilacion...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$p='%BUILD_WORKPATH%';" ^
    "if ($p -and (Test-Path -LiteralPath $p)) { Remove-Item -LiteralPath $p -Recurse -Force -ErrorAction SilentlyContinue }"
if exist build rmdir /s /q build
pause
