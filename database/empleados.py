from typing import Any, Dict, List, Optional
from .connection import session_db
from .utils import ahora

def obtener_empleados(solo_activos: bool = True) -> List[Dict[str, Any]]:
    query = "SELECT * FROM empleados"
    if solo_activos:
        query += " WHERE activo = 1"
    query += " ORDER BY nombre ASC"
    
    with session_db(dict_rows=True) as conn:
        return conn.execute(query).fetchall()

def obtener_empleado_por_id(empleado_id: int) -> Optional[Dict[str, Any]]:
    with session_db(dict_rows=True) as conn:
        return conn.execute("SELECT * FROM empleados WHERE id = ?", (empleado_id,)).fetchone()

def crear_empleado(rut: str, nombre: str, cargo: str, sueldo_base: float, email: str = "", telefono: str = "") -> int:
    with session_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO empleados (rut, nombre, cargo, sueldo_base, email, telefono, fecha_ingreso, activo)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (rut, nombre, cargo, sueldo_base, email, telefono, ahora())
        )
        return cursor.lastrowid

def actualizar_empleado(empleado_id: int, **kwargs) -> bool:
    if not kwargs:
        return False
    
    # Sanitizar: solo permitir columnas válidas
    columnas_validas = {"rut", "nombre", "cargo", "sueldo_base", "email", "telefono", "activo"}
    kwargs = {k: v for k, v in kwargs.items() if k in columnas_validas}
    if not kwargs:
        return False

    campos = ", ".join([f"{k} = ?" for k in kwargs.keys()])
    valores = list(kwargs.values())
    valores.append(empleado_id)
    
    with session_db() as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE empleados SET {campos} WHERE id = ?", valores)
        return cursor.rowcount > 0

def eliminar_empleado(empleado_id: int) -> bool:
    """Desactiva un empleado (borrado lógico)."""
    with session_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE empleados SET activo = 0 WHERE id = ?", (empleado_id,))
        return cursor.rowcount > 0
