from typing import Any, Dict, List, Optional
from .connection import conectar_db, session_db
from .utils import ahora


def registrar_historial(
    accion: str,
    tabla: Optional[str] = None,
    referencia_id: Optional[int] = None,
    detalles: Optional[str] = None,
    usuario_id: Optional[int] = None,
    conn=None,
) -> None:
    propia = conn is None
    if propia:
        conn = conectar_db()
    try:
        conn.execute(
            """
            INSERT INTO historial (fecha, accion, tabla, referencia_id, detalles, usuario_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (ahora(), accion, tabla, referencia_id, detalles, usuario_id),
        )
        if propia:
            conn.commit()
    finally:
        if propia:
            conn.close()


def registrar_movimiento(
    conn, 
    accion: str, 
    detalles: str, 
    usuario_id: Optional[int] = None,
    tabla: Optional[str] = None,
    referencia_id: Optional[int] = None
) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO historial (fecha, accion, tabla, referencia_id, detalles, usuario_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (ahora(), accion, tabla, referencia_id, detalles, usuario_id),
    )
    conn.commit()


def obtener_historial(limite: int = 200) -> List[Dict[str, Any]]:
    with session_db(dict_rows=True) as conn:
        return conn.execute(
            """
            SELECT h.*, u.nombre as usuario_nombre
            FROM historial h
            LEFT JOIN usuarios u ON h.usuario_id = u.id
            ORDER BY h.fecha DESC, h.id DESC
            LIMIT ?
            """,
            (limite,),
        ).fetchall()