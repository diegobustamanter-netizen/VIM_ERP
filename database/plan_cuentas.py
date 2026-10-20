from typing import Any, Dict, List, Optional
from .connection import session_db

def obtener_plan_cuentas(solo_activos: bool = True) -> List[Dict[str, Any]]:
    """Obtiene el catálogo de cuentas contables."""
    query = "SELECT * FROM plan_cuentas"
    if solo_activos:
        query += " WHERE activo = 1"
    query += " ORDER BY codigo ASC"
    
    with session_db(dict_rows=True) as conn:
        return conn.execute(query).fetchall()

def obtener_cuenta_por_id(cuenta_id: int) -> Optional[Dict[str, Any]]:
    with session_db(dict_rows=True) as conn:
        return conn.execute("SELECT * FROM plan_cuentas WHERE id = ?", (cuenta_id,)).fetchone()

def crear_cuenta_contable(codigo: str, nombre: str, tipo: str, es_inventariable: bool = False) -> int:
    with session_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO plan_cuentas (codigo, nombre, tipo, es_inventariable, activo)
            VALUES (?, ?, ?, ?, 1)
            """,
            (codigo, nombre, tipo, 1 if es_inventariable else 0)
        )
        return cursor.lastrowid

def actualizar_cuenta_contable(cuenta_id: int, **kwargs) -> bool:
    if not kwargs:
        return False
    
    # Sanitizar: solo permitir columnas válidas
    columnas_validas = {"codigo", "nombre", "tipo", "es_inventariable", "activo"}
    kwargs = {k: v for k, v in kwargs.items() if k in columnas_validas}
    if not kwargs:
        return False

    campos = ", ".join([f"{k} = ?" for k in kwargs.keys()])
    valores = list(kwargs.values())
    valores.append(cuenta_id)
    
    with session_db() as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE plan_cuentas SET {campos} WHERE id = ?", valores)
        return cursor.rowcount > 0

def eliminar_cuenta_contable(cuenta_id: int) -> bool:
    """Desactiva una cuenta contable (borrado lógico)."""
    with session_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE plan_cuentas SET activo = 0 WHERE id = ?", (cuenta_id,))
        return cursor.rowcount > 0
