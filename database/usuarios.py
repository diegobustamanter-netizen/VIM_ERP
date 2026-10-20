from typing import Any, Dict, List
from .connection import session_db
from .utils import ahora
from .historial import registrar_historial


# ============================================================
# CONSTANTES
# ============================================================

MODULOS_DISPONIBLES = [
    "pos", "inventario", "productos", "reportes",
    "compras", "caja", "usuarios", "configuracion", "backup"
]


# ============================================================
# CRUD USUARIOS
# ============================================================

def crear_usuario(username: str, password_hash: str, nombre: str, rol: str = "cajero", responsable_id: int = None) -> int:
    with session_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO usuarios (username, password_hash, nombre, rol, activo, fecha_creacion)
            VALUES (?, ?, ?, ?, 1, ?)
            """,
            (username.strip(), password_hash, nombre.strip(), rol.strip(), ahora()),
        )
        usuario_id = cursor.lastrowid

        # Crear permisos por defecto según rol
        permisos_default = _permisos_default_por_rol(rol.strip())
        for modulo, permitido in permisos_default.items():
            cursor.execute(
                "INSERT OR IGNORE INTO permisos_modulo (usuario_id, modulo, permitido) VALUES (?, ?, ?)",
                (usuario_id, modulo, 1 if permitido else 0)
            )

        conn.commit()

    registrar_historial("crear_usuario", "usuarios", usuario_id, f"Usuario: {username}", usuario_id=responsable_id)
    return usuario_id


def actualizar_usuario(usuario_id: int, username: str, nombre: str, rol: str, password_hash: str = None, responsable_id: int = None) -> bool:
    with session_db() as conn:
        cursor = conn.cursor()
        if password_hash:
            cursor.execute(
                "UPDATE usuarios SET username=?, nombre=?, password_hash=?, rol=? WHERE id=?",
                (username.strip(), nombre.strip(), password_hash, rol.strip(), usuario_id)
            )
        else:
            cursor.execute(
                "UPDATE usuarios SET username=?, nombre=?, rol=? WHERE id=?",
                (username.strip(), nombre.strip(), rol.strip(), usuario_id)
            )
        conn.commit()

    registrar_historial("actualizar_usuario", "usuarios", usuario_id, f"Usuario: {username}", usuario_id=responsable_id)
    return True


def desactivar_usuario(usuario_id: int, responsable_id: int = None) -> bool:
    with session_db() as conn:
        conn.execute("UPDATE usuarios SET activo=0 WHERE id=?", (usuario_id,))
        conn.commit()
    registrar_historial("desactivar_usuario", "usuarios", usuario_id, "Desactivado", usuario_id=responsable_id)
    return True


def activar_usuario(usuario_id: int, responsable_id: int = None) -> bool:
    with session_db() as conn:
        conn.execute("UPDATE usuarios SET activo=1 WHERE id=?", (usuario_id,))
        conn.commit()
    registrar_historial("activar_usuario", "usuarios", usuario_id, "Reactivado", usuario_id=responsable_id)
    return True


def eliminar_usuario(usuario_id: int, responsable_id: int = None) -> bool:
    with session_db() as conn:
        conn.execute("DELETE FROM permisos_modulo WHERE usuario_id=?", (usuario_id,))
        conn.execute("DELETE FROM usuarios WHERE id=?", (usuario_id,))
        conn.commit()
    registrar_historial("eliminar_usuario", "usuarios", usuario_id, "Eliminado permanentemente", usuario_id=responsable_id)
    return True


def obtener_usuarios() -> List[Dict[str, Any]]:
    with session_db(dict_rows=True) as conn:
        return conn.execute(
            "SELECT id, username, nombre, rol, activo, fecha_creacion, ultimo_acceso FROM usuarios ORDER BY id"
        ).fetchall()


# ============================================================
# PERMISOS GRANULARES POR MÓDULO
# ============================================================

def obtener_permisos_usuario(usuario_id: int) -> Dict[str, bool]:
    """Retorna dict {modulo: True/False} para el usuario dado."""
    resultado = {m: False for m in MODULOS_DISPONIBLES}
    with session_db() as conn:
        rows = conn.execute(
            "SELECT modulo, permitido FROM permisos_modulo WHERE usuario_id = ?",
            (usuario_id,)
        ).fetchall()
        for modulo, permitido in rows:
            if modulo in resultado:
                resultado[modulo] = bool(permitido)
    return resultado


def guardar_permisos_usuario(usuario_id: int, permisos: Dict[str, bool], responsable_id: int = None) -> bool:
    """Guarda/actualiza los permisos del usuario. permisos = {modulo: True/False}."""
    with session_db() as conn:
        cursor = conn.cursor()
        for modulo, permitido in permisos.items():
            if modulo not in MODULOS_DISPONIBLES:
                continue
            cursor.execute(
                """
                INSERT INTO permisos_modulo (usuario_id, modulo, permitido)
                VALUES (?, ?, ?)
                ON CONFLICT(usuario_id, modulo) DO UPDATE SET permitido = excluded.permitido
                """,
                (usuario_id, modulo, 1 if permitido else 0)
            )
        conn.commit()

    registrar_historial("actualizar_permisos", "permisos_modulo", usuario_id, f"Permisos actualizados", usuario_id=responsable_id)
    return True


def _permisos_default_por_rol(rol: str) -> Dict[str, bool]:
    """Retorna permisos por defecto según el rol."""
    if rol == "administrador":
        return {m: True for m in MODULOS_DISPONIBLES}
    elif rol == "supervisor":
        permitidos = {"pos", "inventario", "productos", "reportes", "compras", "caja"}
        return {m: m in permitidos for m in MODULOS_DISPONIBLES}
    else:  # cajero
        permitidos = {"pos", "caja"}
        return {m: m in permitidos for m in MODULOS_DISPONIBLES}