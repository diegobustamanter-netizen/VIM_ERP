"""
Logging centralizado para VIM ERP.
Todos los módulos deben importar `logger` desde aquí.
"""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from config import DATA_DIR

# Determinar la carpeta de logs
if getattr(sys, 'frozen', False):
    # En ejecutable: los logs van a AppData junto a la base de datos.
    _BASE_DIR = DATA_DIR
else:
    # En desarrollo: relativo al script
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))

_LOG_DIR = os.path.join(_BASE_DIR, "logs")
os.makedirs(_LOG_DIR, exist_ok=True)

_LOG_FILE = os.path.join(_LOG_DIR, "vim_erp.log")

# Formato: [2026-05-04 20:00:00] [INFO] modulo.sub: Mensaje
_FORMAT = "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_formato = logging.Formatter(_FORMAT, datefmt=_DATE_FORMAT)

# Archivo con rotación: un POS puede estar años encendido y un log sin límite
# termina ocupando cientos de megas. Se guardan 1 MB x 3 archivos.
_handler_file = RotatingFileHandler(
    _LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
)
_handler_file.setFormatter(_formato)

# Logger base del proyecto
logger = logging.getLogger("vim_erp")
logger.setLevel(logging.INFO)
logger.addHandler(_handler_file)

# Consola solo si existe de verdad. El ejecutable se compila con
# console=False (ver VIM_ERP.spec), y ahí sys.stdout es None: agregar el
# handler igual hacía que cada llamada al log fallara por dentro.
if sys.stdout is not None:
    _handler_console = logging.StreamHandler(sys.stdout)
    _handler_console.setFormatter(_formato)
    _handler_console.setLevel(logging.WARNING)  # Solo warnings+ en consola
    logger.addHandler(_handler_console)

# Estos mensajes ya se manejan acá: que no suban también al logger raíz.
logger.propagate = False


def get_logger(nombre_modulo: str) -> logging.Logger:
    """Retorna un logger hijo para un módulo específico.
    
    Uso:
        from vim_logger import get_logger
        log = get_logger("pos.ticket")
        log.info("Venta confirmada")
    """
    return logger.getChild(nombre_modulo)
