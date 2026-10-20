from database.connection import session_db
from vim_logger import get_logger

_log = get_logger("configuracion")

def get_config(clave, default=""):
    """Obtiene un valor de la tabla configuracion."""
    try:
        with session_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT valor FROM configuracion WHERE clave = ?", (clave,))
            row = cursor.fetchone()
            if row:
                return row[0]
            return default
    except Exception as e:
        _log.error(f"Error obteniendo configuracion '{clave}': {e}")
        return default

def get_configs(claves):
    """Obtiene múltiples valores de una vez. Retorna diccionario con resultados."""
    try:
        placeholders = ",".join(["?"] * len(claves))
        with session_db() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT clave, valor FROM configuracion WHERE clave IN ({placeholders})", tuple(claves))
            rows = cursor.fetchall()
            resultado = {c: "" for c in claves}
            for clave, valor in rows:
                resultado[clave] = valor
            return resultado
    except Exception as e:
        _log.error(f"Error obteniendo configuraciones: {e}")
        return {c: "" for c in claves}

def set_config(clave, valor, descripcion=""):
    """Inserta o actualiza un valor en la configuración."""
    try:
        with session_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT clave FROM configuracion WHERE clave = ?", (clave,))
            if cursor.fetchone():
                cursor.execute("UPDATE configuracion SET valor = ? WHERE clave = ?", (str(valor), clave))
            else:
                cursor.execute(
                    "INSERT INTO configuracion (clave, valor, descripcion) VALUES (?, ?, ?)",
                    (clave, str(valor), descripcion)
                )
            conn.commit()
            return True
    except Exception as e:
        _log.error(f"Error guardando configuracion '{clave}': {e}")
        return False
