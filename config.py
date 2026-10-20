import sys
import os

# ============================================================
# RUTAS
# ============================================================


APP_DATA_FOLDER = "VIM_ERP"


def obtener_directorio_datos_usuario():
    """Carpeta estable y escribible para datos de la app en Windows."""
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
    if base:
        return os.path.join(base, APP_DATA_FOLDER)
    return os.path.join(os.path.expanduser("~"), f".{APP_DATA_FOLDER.lower()}")

# Detectar si la app esta empaquetada (congelada) con PyInstaller
if getattr(sys, 'frozen', False):
    # En ejecutable: los assets estan en el directorio temporal de PyInstaller
    BASE_DIR = sys._MEIPASS
    # Los datos persistentes deben ir a AppData, no junto al .exe distribuido.
    DATA_DIR = obtener_directorio_datos_usuario()
else:
    # En desarrollo: todo en el mismo directorio del script
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = BASE_DIR

DATA_DIR = os.path.abspath(DATA_DIR)
os.makedirs(DATA_DIR, exist_ok=True)

ASSETS_DIR = os.path.join(BASE_DIR, "Assets")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.png")
ICO_PATH = os.path.join(ASSETS_DIR, "icono.ico")

# Directorio de Base de Datos persistente
DB_DIR = os.path.join(DATA_DIR, "database")

# Asegurar que el directorio de la base de datos exista
os.makedirs(DB_DIR, exist_ok=True)

DB_NAME = os.path.join(DB_DIR, "vim_erp.db")

# ============================================================
# COLORES
# ============================================================

COLOR_PRIMARIO = "#002b5c"
COLOR_SECUNDARIO = "#004080"
COLOR_BLANCO = "#ffffff"
COLOR_GRIS = "#f4f6f9"
COLOR_PELIGRO = "#d9534f"
COLOR_PELIGRO_HOVER = "#c9302c"
COLOR_EXITO = "#28a745"
COLOR_INFO = "#17a2b8"
COLOR_ADVERTENCIA = "#ffc107"

# ============================================================
# FUENTES — Se escalan al momento de acceder mediante __getattr__
# ============================================================
# Esto permite que todos los font=FUENTE_TITULO sigan funcionando
# sin cambios, obteniendo automáticamente escalar_fuente() en el
# tamaño cuando son importados (después de inicializar_escala()).

_FONT_RAW = {
    "FUENTE_TITULO":    ("Segoe UI", 30, "bold"),
    "FUENTE_SUBTITULO": ("Segoe UI", 14, "bold"),
    "FUENTE_BOTON":     ("Segoe UI", 10, "bold"),
    "FUENTE_MODULO":    ("Segoe UI", 20, "bold"),
    "FUENTE_LABEL":     ("Segoe UI", 10),
    "FUENTE_INPUT":     ("Segoe UI", 11),
    "FUENTE_FOOTER":    ("Segoe UI", 9),
}


def __getattr__(name):
    """Retorna fuentes con tamaño escalado al acceder como atributo del módulo."""
    if name not in _FONT_RAW:
        raise AttributeError(f"module 'config' has no attribute {name!r}")
    try:
        from ui_scale import escalar_fuente
        family, size, *styles = _FONT_RAW[name]
        return (family, escalar_fuente(size), *styles)
    except Exception:
        # Fallback: fuente sin escalar si ui_scale no está inicializada
        return _FONT_RAW[name]
