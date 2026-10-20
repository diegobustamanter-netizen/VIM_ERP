# VIM ERP

Sistema de punto de venta y administración para pequeños negocios, hecho en Python (Tkinter) para Windows. Sirve tanto para negocios que venden productos como para negocios de servicios (peluquerías, talleres, etc.).

## Funciones

- Punto de venta (POS) con comprobantes en impresoras térmicas de 58 mm y 80 mm (ESC/POS) o en PDF. No emite boletas electrónicas del SII
- Modo productos (con inventario) o modo servicios (sin stock), elegido en el primer inicio
- Productos, categorías e inventario con historial de movimientos
- Compras y proveedores
- Caja: apertura, cierre y movimientos
- Reportes de ventas y reportes financieros (estado de resultados, IVA), exportables a Excel
- Empleados y liquidaciones
- Usuarios, roles y permisos por módulo
- Respaldos de la base de datos

## Descargar

Descarga la última versión de `VIM_ERP.exe` en la sección [Releases](../../releases). No requiere instalación.

En el primer inicio, el usuario es `admin` y la clave inicial aparece en la pantalla de acceso. Un asistente te guía para elegir el tipo de negocio y configurar la recuperación de clave. Cambia la clave del administrador apenas entres.

Los datos se guardan en `%LOCALAPPDATA%\VIM_ERP`.

## Ejecutar desde el código

Requiere Python 3.10 o superior en Windows 10/11.

```bat
pip install -r requirements.txt
python ventana_principal.py
```

También puedes usar `instalar_dependencias.bat` y después `run.bat`.

## Pruebas automáticas

```bat
test.bat
```

Las pruebas usan una base temporal: tu base real no se toca. Más detalles en [tests/README.md](tests/README.md).

## Compilar el ejecutable

```bat
pip install pyinstaller
build.bat
```

El ejecutable queda en `dist\VIM_ERP.exe`.

## Publicar una versión

`crear_paquete_distribucion.bat` corre las pruebas, compila el `.exe` y arma `..\VIM_ERP_v1.0_Windows.zip` con el ejecutable, el manual, el LEEME, la licencia y la huella SHA-256. La versión se cambia en la línea `set "VERSION=..."` del mismo archivo.

## Licencia

MIT. Ver [LICENSE](LICENSE).
