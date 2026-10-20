import os
import shutil
import sqlite3
from datetime import datetime
from typing import Dict, List

from config import DB_NAME, DATA_DIR
from .utils import ahora
from vim_logger import get_logger

_log = get_logger("database.backup")


# ============================================================
# CONSTANTES
# ============================================================

BACKUP_DIR = os.path.join(DATA_DIR, "backups")


def _asegurar_directorio():
    """Crea el directorio de backups si no existe."""
    os.makedirs(BACKUP_DIR, exist_ok=True)


# ============================================================
# OPERACIONES DE BACKUP
# ============================================================

def crear_backup() -> str:
    """
    Crea una copia de seguridad de la base de datos principal.
    Retorna la ruta completa del archivo de backup creado.
    """
    _asegurar_directorio()

    if not os.path.exists(DB_NAME):
        raise FileNotFoundError(f"No se encontró la base de datos: {DB_NAME}")

    timestamp = ahora("%Y%m%d_%H%M%S")
    nombre_backup = f"vim_erp_backup_{timestamp}.db"
    ruta_destino = os.path.join(BACKUP_DIR, nombre_backup)

    # Usar la API de SQLite para backup en caliente (es el único método seguro en modo WAL)
    try:
        # Forzar un checkpoint antes del backup para asegurar que el .db esté al día
        conn_temp = sqlite3.connect(DB_NAME)
        conn_temp.execute("PRAGMA wal_checkpoint(TRUNCATE)")

        destino = sqlite3.connect(ruta_destino)
        conn_temp.backup(destino)
        destino.close()
        conn_temp.close()
    except Exception as e:
        # Camino de emergencia. Copiar solo el .db en modo WAL puede dejar
        # afuera las últimas ventas, que todavía viven en el archivo -wal, y
        # el backup parecería válido igual. Por eso se copian también los
        # archivos auxiliares: al abrirlo, SQLite reconstruye lo que falta.
        _log.warning(f"Error usando API backup: {e}. Intentando copia directa...")
        shutil.copy2(DB_NAME, ruta_destino)

        for sufijo in ("-wal", "-shm"):
            origen_aux = DB_NAME + sufijo
            if os.path.exists(origen_aux):
                try:
                    shutil.copy2(origen_aux, ruta_destino + sufijo)
                except Exception as e_aux:
                    _log.error(
                        f"Backup posiblemente INCOMPLETO: no se pudo copiar "
                        f"'{origen_aux}'. Las últimas operaciones podrían faltar. ({e_aux})"
                    )

    return ruta_destino


def listar_backups() -> List[Dict]:
    """
    Escanea la carpeta de backups y retorna lista de backups disponibles.
    Ordenados del más reciente al más antiguo.
    """
    _asegurar_directorio()

    backups = []
    for archivo in os.listdir(BACKUP_DIR):
        if archivo.endswith(".db") and archivo.startswith("vim_erp_backup_"):
            ruta = os.path.join(BACKUP_DIR, archivo)
            stat = os.stat(ruta)
            tamaño_mb = stat.st_size / (1024 * 1024)
            fecha_mod = datetime.fromtimestamp(stat.st_mtime)

            backups.append({
                "nombre": archivo,
                "ruta": ruta,
                "tamaño_mb": round(tamaño_mb, 2),
                "fecha": fecha_mod.strftime("%d-%m-%Y %H:%M:%S"),
                "fecha_sort": fecha_mod,
            })

    backups.sort(key=lambda b: b["fecha_sort"], reverse=True)
    return backups


def restaurar_backup(ruta_backup: str) -> bool:
    """
    Restaura la base de datos desde un archivo de backup.
    Crea un backup de seguridad antes de restaurar.
    """
    if not os.path.exists(ruta_backup):
        raise FileNotFoundError(f"Archivo de backup no encontrado: {ruta_backup}")

    # Validar que es una DB SQLite válida
    try:
        conn = sqlite3.connect(ruta_backup)
        conn.execute("SELECT COUNT(*) FROM sqlite_master")
        conn.close()
    except sqlite3.DatabaseError:
        raise ValueError("El archivo seleccionado no es una base de datos SQLite válida.")

    # 1. Crear backup de seguridad preventivo del estado ACTUAL
    _asegurar_directorio()
    timestamp = ahora("%Y%m%d_%H%M%S")
    seguridad = os.path.join(BACKUP_DIR, f"pre_restauracion_{timestamp}.db")
    
    if os.path.exists(DB_NAME):
        try:
            # Intentamos backup limpio (con checkpoint)
            c_actual = sqlite3.connect(DB_NAME)
            c_actual.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            c_dest = sqlite3.connect(seguridad)
            c_actual.backup(c_dest)
            c_dest.close()
            c_actual.close()
        except Exception:
            # Fallback a copia simple si está muy bloqueado
            try:
                shutil.copy2(DB_NAME, seguridad)
            except Exception as e:
                # Quedarse sin copia de seguridad antes de restaurar es grave:
                # si la restauración sale mal no hay a dónde volver.
                _log.error(
                    f"No se pudo crear la copia de seguridad previa en '{seguridad}': {e}"
                )

    # 2. RESTAURAR USANDO LA API NATIVA DE SQLITE
    # sqlite3.backup() funciona correctamente incluso con la BD en uso (WAL activo),
    # sin necesidad de borrar ni bloquear archivos WAL/SHM.
    try:
        conn_origen = sqlite3.connect(ruta_backup)
        conn_destino = sqlite3.connect(DB_NAME)
        conn_origen.backup(conn_destino)
        conn_destino.close()
        conn_origen.close()
    except Exception as e:
        raise PermissionError(
            f"No se pudo restaurar la base de datos.\n"
            f"Asegúrese de cerrar el Punto de Venta antes de restaurar.\n\n"
            f"Detalle técnico: {e}"
        )

    return True


def eliminar_backup(ruta_backup: str) -> bool:
    """Elimina un archivo de backup."""
    if os.path.exists(ruta_backup):
        os.remove(ruta_backup)
        return True
    return False


def obtener_info_sistema() -> Dict:
    """Retorna información del sistema: versión, tamaño DB, etc."""
    db_size = 0
    if os.path.exists(DB_NAME):
        db_size = os.path.getsize(DB_NAME) / (1024 * 1024)

    backups = listar_backups()
    ultimo_backup = backups[0]["fecha"] if backups else "Nunca"

    # Contadores de registros
    conteos = {}
    try:
        conn = sqlite3.connect(DB_NAME)
        for tabla in ["productos", "ventas", "usuarios", "proveedores"]:
            try:
                # `tabla` viene de la lista fija de arriba, nunca de entrada
                # del usuario: la interpolación es segura.
                count = conn.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
                conteos[tabla] = count
            except Exception as e:
                _log.warning(f"No se pudo contar la tabla '{tabla}': {e}")
                conteos[tabla] = 0
        conn.close()
    except Exception as e:
        _log.warning(f"No se pudieron leer los conteos de la base: {e}")

    return {
        "version": "VIM ERP v1.0",
        "db_nombre": os.path.basename(DB_NAME),
        "db_tamaño_mb": round(db_size, 2),
        "ultimo_backup": ultimo_backup,
        "total_backups": len(backups),
        "registros": conteos,
    }
