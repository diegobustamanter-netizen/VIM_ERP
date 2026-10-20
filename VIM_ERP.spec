# -*- mode: python ; coding: utf-8 -*-
# ============================================================
# VIM ERP - PyInstaller Spec File
# Genera un ejecutable profesional de un solo archivo (.exe)
# ============================================================

import os

block_cipher = None

# Ruta base del proyecto
BASE_DIR = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    ['ventana_principal.py'],
    pathex=[BASE_DIR],
    binaries=[],
    datas=[
        ('Assets', 'Assets'),
    ],
    hiddenimports=[
        # === Pillow ===
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'PIL._tkinter_finder',

        # === Tkinter (explícito para PyInstaller) ===
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.filedialog',
        'tkinter.simpledialog',

        # === Reportes / Gráficos ===
        'matplotlib',
        'matplotlib.pyplot',
        'matplotlib.backends.backend_tkagg',
        'matplotlib.ticker',
        'openpyxl',
        'openpyxl.styles',
        'openpyxl.utils',

        # === python-docx (genera informes) ===
        'docx',
        'docx.shared',
        'docx.enum.text',
        'docx.oxml.ns',
        'docx.oxml',

        # === Calendario (filtros de fecha) ===
        'tkcalendar',

        # === Módulos del proyecto (seguridad para imports dinámicos) ===
        'config',
        'ui_scale',
        'vim_logger',
        'generar_informe',
        'database',
        'database.connection',
        'database.schema',
        'database.seed',
        'database.productos',
        'database.ventas',
        'database.caja',
        'database.categorias',
        'database.proveedores',
        'database.compras',
        'database.empleados',
        'database.historial',
        'database.usuarios',
        'database.backup',
        'database.utils',
        'database.finanzas_utils',
        'database.reportes_financieros',
        'database.liquidaciones',
        'database.plan_cuentas',
        'database.negocio',
        'modulos.utils_globales',
        'modulos.productos',
        'modulos.productos.controller',
        'modulos.productos.tabla',
        'modulos.productos.form',
        'modulos.productos.acciones',
        'modulos.productos.historial',
        'modulos.productos.utils',
        'modulos.pos',
        'modulos.pos.pos_main',
        'modulos.pos.pos_ui',
        'modulos.pos.pos_ticket',
        'modulos.pos.pos_busqueda',
        'modulos.pos.pos_calculos',
        'modulos.pos.pos_navegacion',
        'modulos.pos.pos_utils',
        'modulos.caja',
        'modulos.caja.caja_main',
        'modulos.caja.caja_ui',
        'modulos.ventas_reportes',
        'modulos.ventas_reportes.ventas_main',
        'modulos.ventas_reportes.ventas_ui',
        'modulos.compras',
        'modulos.compras.compras_main',
        'modulos.compras.compras_ui',
        'modulos.configuracion',
        'modulos.configuracion.main',
        'modulos.configuracion.ui',
        'modulos.configuracion.utils',
        'modulos.configuracion.secciones',
        'modulos.configuracion.secciones.acerca_de',
        'modulos.configuracion.secciones.empresa',
        'modulos.configuracion.secciones.finanzas',
        'modulos.configuracion.secciones.sistema',
        'modulos.configuracion.secciones.ventas',
        'modulos.usuarios',
        'modulos.usuarios.usuarios_main',
        'modulos.seguridad',
        'modulos.seguridad.sesion',
        'modulos.seguridad.auth',
        'modulos.seguridad.login_ui',
        'modulos.seguridad.autorizacion_ui',
        'modulos.seguridad.recuperacion_ui',
        'modulos.seguridad.rate_limiter',
        'modulos.backup',
        'modulos.backup.backup_main',
        'modulos.impresion',
        'modulos.impresion.impresora_termica',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Excluir módulos innecesarios para reducir tamaño
        'pandas',
        'scipy',
        'pytest',
        'unittest',
        'test',
        'tests',
        'IPython',
        'jupyter',
        'notebook',
        'setuptools',
        'pip',
        'pkg_resources',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='VIM_ERP',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,             # Sin ventana de consola (app GUI)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='Assets\\icono.ico',
    version='version_info.txt',  # Metadatos profesionales en Propiedades del .exe
)
