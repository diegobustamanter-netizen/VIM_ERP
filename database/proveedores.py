from typing import Any, Dict, List
from .connection import session_db
from .utils import ahora
from .historial import registrar_historial


def crear_proveedor(
    nombre: str,
    rut: str = "",
    telefono: str = "",
    email: str = "",
    direccion: str = "",
    contacto: str = "",
) -> int:
    with session_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO proveedores (
                nombre, rut, telefono, email, direccion, contacto,
                activo, fecha_creacion
            )
            VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (
                nombre.strip(),
                rut.strip(),
                telefono.strip(),
                email.strip(),
                direccion.strip(),
                contacto.strip(),
                ahora(),
            ),
        )
        proveedor_id = cursor.lastrowid

    registrar_historial("crear_proveedor", "proveedores", proveedor_id, f"Proveedor: {nombre}")
    return proveedor_id


def obtener_proveedores() -> List[Dict[str, Any]]:
    with session_db(dict_rows=True) as conn:
        return conn.execute(
            "SELECT * FROM proveedores WHERE activo = 1 ORDER BY nombre ASC"
        ).fetchall()

def actualizar_proveedor(proveedor_id: int, **kwargs) -> bool:
    if not kwargs:
        return False
    
    # Sanitizar: solo permitir columnas válidas
    columnas_validas = {"nombre", "rut", "telefono", "email", "direccion", "contacto", "activo"}
    kwargs = {k: v for k, v in kwargs.items() if k in columnas_validas}
    if not kwargs:
        return False

    campos = ", ".join([f"{k} = ?" for k in kwargs.keys()])
    valores = list(kwargs.values())
    valores.append(proveedor_id)
    
    with session_db() as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE proveedores SET {campos} WHERE id = ?", valores)
    
    registrar_historial("actualizar_proveedor", "proveedores", proveedor_id, f"Campos actualizados: {list(kwargs.keys())}")
    return True

def eliminar_proveedor(proveedor_id: int) -> bool:
    """Desactiva un proveedor (borrado lógico)."""
    with session_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE proveedores SET activo = 0 WHERE id = ?", (proveedor_id,))
    
    registrar_historial("eliminar_proveedor", "proveedores", proveedor_id, "Proveedor desactivado")
    return True