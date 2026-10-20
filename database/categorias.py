from typing import Any, Dict, List
from .connection import session_db
from .utils import ahora
from .historial import registrar_historial


def crear_categoria(nombre: str, descripcion: str = "") -> int:
    with session_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO categorias (nombre, descripcion, activa, fecha_creacion)
            VALUES (?, ?, 1, ?)
            """,
            (nombre.strip(), descripcion.strip(), ahora()),
        )
        categoria_id = cursor.lastrowid
        conn.commit()

    registrar_historial("crear_categoria", "categorias", categoria_id, f"Categoría: {nombre}")
    return categoria_id


def obtener_categorias() -> List[Dict[str, Any]]:
    with session_db(dict_rows=True) as conn:
        return conn.execute(
            "SELECT * FROM categorias WHERE activa = 1 ORDER BY nombre ASC"
        ).fetchall()