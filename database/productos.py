from typing import Any, Dict, List, Optional

from .connection import session_db
from .utils import ahora
from .historial import registrar_historial


# ============================================================
# HELPERS INTERNOS
# ============================================================
def _normalizar_texto(valor: Optional[str]) -> str:
    return (valor or "").strip()


def _resolver_categoria_id(
    conn,
    categoria_id: Optional[int] = None,
    categoria_texto: str = "",
    crear_si_no_existe: bool = False,
) -> Optional[int]:
    if categoria_id:
        return int(categoria_id)

    categoria_texto = _normalizar_texto(categoria_texto)
    if not categoria_texto:
        return None

    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id
        FROM categorias
        WHERE nombre = ? COLLATE NOCASE
        LIMIT 1
        """,
        (categoria_texto,),
    )
    fila = cursor.fetchone()
    if fila:
        return fila[0]

    if crear_si_no_existe:
        cursor.execute(
            """
            INSERT INTO categorias (nombre, activa, fecha_creacion)
            VALUES (?, 1, ?)
            """,
            (categoria_texto, ahora()),
        )
        return cursor.lastrowid

    return None


def _resolver_proveedor_id(
    conn,
    proveedor_id: Optional[int] = None,
    proveedor_texto: str = "",
    crear_si_no_existe: bool = False,
) -> Optional[int]:
    if proveedor_id:
        return int(proveedor_id)

    proveedor_texto = _normalizar_texto(proveedor_texto)
    if not proveedor_texto:
        return None

    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id
        FROM proveedores
        WHERE nombre = ? COLLATE NOCASE
        LIMIT 1
        """,
        (proveedor_texto,),
    )
    fila = cursor.fetchone()
    if fila:
        return fila[0]

    if crear_si_no_existe:
        cursor.execute(
            """
            INSERT INTO proveedores (nombre, activo, fecha_creacion)
            VALUES (?, 1, ?)
            """,
            (proveedor_texto, ahora()),
        )
        return cursor.lastrowid

    return None


def obtener_categoria_id_por_nombre(
    nombre: str,
    crear_si_no_existe: bool = False
) -> Optional[int]:
    with session_db() as conn:
        categoria_id = _resolver_categoria_id(
            conn,
            categoria_texto=nombre,
            crear_si_no_existe=crear_si_no_existe
        )
        conn.commit()
        return categoria_id


def obtener_proveedor_id_por_nombre(
    nombre: str,
    crear_si_no_existe: bool = False
) -> Optional[int]:
    with session_db() as conn:
        proveedor_id = _resolver_proveedor_id(
            conn,
            proveedor_texto=nombre,
            crear_si_no_existe=crear_si_no_existe
        )
        conn.commit()
        return proveedor_id


# ============================================================
# CREAR PRODUCTO
# ============================================================
def crear_producto(
    codigo_barras: str = "",
    codigo_pos: str = "",
    nombre: str = "",
    descripcion: str = "",
    tipo_item: str = "producto",
    categoria_id: Optional[int] = None,
    proveedor_id: Optional[int] = None,
    categoria_texto: str = "",
    proveedor_texto: str = "",
    precio_compra: float = 0,
    precio_venta: float = 0,
    precio_por_kilo: float = 0,
    stock: float = 0,
    stock_minimo: float = 0,
    unidad_medida: str = "unidad",
    tipo_venta: str = "unidad",
    permite_descuento: int = 1,
    crear_relaciones_si_no_existen: bool = False,
) -> int:
    nombre = _normalizar_texto(nombre)
    descripcion = _normalizar_texto(descripcion)
    codigo_barras = _normalizar_texto(codigo_barras)
    codigo_pos = _normalizar_texto(codigo_pos)
    tipo_item = _normalizar_texto(tipo_item) or "producto"
    unidad_medida = _normalizar_texto(unidad_medida) or "unidad"
    tipo_venta = _normalizar_texto(tipo_venta) or "unidad"

    if not nombre:
        raise ValueError("El nombre del producto es obligatorio.")

    if not codigo_barras and not codigo_pos:
        raise ValueError("Debes ingresar código de barras o código POS.")

    with session_db() as conn:
        cursor = conn.cursor()

        categoria_id = _resolver_categoria_id(
            conn,
            categoria_id=categoria_id,
            categoria_texto=categoria_texto,
            crear_si_no_existe=crear_relaciones_si_no_existen,
        )

        proveedor_id = _resolver_proveedor_id(
            conn,
            proveedor_id=proveedor_id,
            proveedor_texto=proveedor_texto,
            crear_si_no_existe=crear_relaciones_si_no_existen,
        )

        cursor.execute(
            """
            INSERT INTO productos (
                codigo_barras,
                codigo_pos,
                nombre,
                descripcion,
                tipo_item,
                categoria_id,
                proveedor_id,
                precio_compra,
                precio_venta,
                precio_por_kilo,
                stock,
                stock_minimo,
                unidad_medida,
                tipo_venta,
                permite_descuento,
                activo,
                fecha_creacion
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (
                codigo_barras or None,
                codigo_pos or None,
                nombre,
                descripcion,
                tipo_item,
                categoria_id,
                proveedor_id,
                float(precio_compra),
                float(precio_venta),
                float(precio_por_kilo),
                float(stock),
                float(stock_minimo),
                unidad_medida,
                tipo_venta,
                int(permite_descuento),
                ahora(),
            ),
        )

        producto_id = cursor.lastrowid
        conn.commit()

    registrar_historial(
        "crear_producto",
        "productos",
        producto_id,
        f"Producto: {nombre} | categoria_id={categoria_id} | proveedor_id={proveedor_id}",
    )
    return producto_id


# ============================================================
# ACTUALIZAR PRODUCTO
# ============================================================
def actualizar_producto(
    producto_id: int,
    crear_relaciones_si_no_existen: bool = False,
    **campos
) -> bool:
    if not campos:
        return False

    columnas_validas = {
        "codigo_barras",
        "codigo_pos",
        "nombre",
        "descripcion",
        "tipo_item",
        "categoria_id",
        "proveedor_id",
        "precio_compra",
        "precio_venta",
        "precio_por_kilo",
        "stock",
        "stock_minimo",
        "unidad_medida",
        "tipo_venta",
        "permite_descuento",
        "activo",
    }

    categoria_texto = campos.pop("categoria_texto", "")
    proveedor_texto = campos.pop("proveedor_texto", "")

    actualizables = {k: v for k, v in campos.items() if k in columnas_validas}
    if not actualizables and not categoria_texto and not proveedor_texto:
        return False

    with session_db() as conn:
        if categoria_texto or ("categoria_id" in actualizables):
            actualizables["categoria_id"] = _resolver_categoria_id(
                conn,
                categoria_id=actualizables.get("categoria_id"),
                categoria_texto=categoria_texto,
                crear_si_no_existe=crear_relaciones_si_no_existen,
            )

        if proveedor_texto or ("proveedor_id" in actualizables):
            actualizables["proveedor_id"] = _resolver_proveedor_id(
                conn,
                proveedor_id=actualizables.get("proveedor_id"),
                proveedor_texto=proveedor_texto,
                crear_si_no_existe=crear_relaciones_si_no_existen,
            )

        if "codigo_barras" in actualizables:
            actualizables["codigo_barras"] = _normalizar_texto(actualizables["codigo_barras"]) or None

        if "codigo_pos" in actualizables:
            actualizables["codigo_pos"] = _normalizar_texto(actualizables["codigo_pos"]) or None

        if "nombre" in actualizables:
            actualizables["nombre"] = _normalizar_texto(actualizables["nombre"])

        if "descripcion" in actualizables:
            actualizables["descripcion"] = _normalizar_texto(actualizables["descripcion"])

        if "tipo_item" in actualizables:
            actualizables["tipo_item"] = _normalizar_texto(actualizables["tipo_item"]) or "producto"

        if "unidad_medida" in actualizables:
            actualizables["unidad_medida"] = _normalizar_texto(actualizables["unidad_medida"])

        if "tipo_venta" in actualizables:
            actualizables["tipo_venta"] = _normalizar_texto(actualizables["tipo_venta"])

        actualizables["fecha_actualizacion"] = ahora()

        sets = ", ".join(f"{campo} = ?" for campo in actualizables.keys())
        valores = list(actualizables.values()) + [producto_id]

        conn.execute(
            f"UPDATE productos SET {sets} WHERE id = ?",
            valores
        )
        conn.commit()

    registrar_historial(
        "actualizar_producto",
        "productos",
        producto_id,
        f"Campos: {', '.join(actualizables.keys())}",
    )
    return True


# ============================================================
# ELIMINAR PRODUCTO (BAJA LÓGICA)
# ============================================================
def eliminar_producto(producto_id: int) -> bool:
    with session_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE productos
            SET activo = 0,
                fecha_actualizacion = ?
            WHERE id = ?
            """,
            (ahora(), producto_id),
        )
        conn.commit()

        if cursor.rowcount == 0:
            return False

    registrar_historial(
        "eliminar_producto",
        "productos",
        producto_id,
        "Baja lógica de producto",
    )
    return True


# ============================================================
# OBTENER PRODUCTO
# ============================================================
def obtener_producto_por_id(producto_id: int) -> Optional[Dict[str, Any]]:
    with session_db(dict_rows=True) as conn:
        return conn.execute(
            """
            SELECT p.*,
                   c.nombre AS categoria_nombre,
                   pr.nombre AS proveedor_nombre
            FROM productos p
            LEFT JOIN categorias c ON p.categoria_id = c.id
            LEFT JOIN proveedores pr ON p.proveedor_id = pr.id
            WHERE p.id = ?
            """,
            (producto_id,),
        ).fetchone()


def obtener_producto_por_codigo_barras(codigo_barras: str) -> Optional[Dict[str, Any]]:
    with session_db(dict_rows=True) as conn:
        return conn.execute(
            """
            SELECT p.*,
                   c.nombre AS categoria_nombre,
                   pr.nombre AS proveedor_nombre
            FROM productos p
            LEFT JOIN categorias c ON p.categoria_id = c.id
            LEFT JOIN proveedores pr ON p.proveedor_id = pr.id
            WHERE p.codigo_barras = ?
              AND p.activo = 1
            """,
            (_normalizar_texto(codigo_barras),),
        ).fetchone()


def obtener_producto_por_codigo_pos(codigo_pos: str) -> Optional[Dict[str, Any]]:
    with session_db(dict_rows=True) as conn:
        return conn.execute(
            """
            SELECT p.*,
                   c.nombre AS categoria_nombre,
                   pr.nombre AS proveedor_nombre
            FROM productos p
            LEFT JOIN categorias c ON p.categoria_id = c.id
            LEFT JOIN proveedores pr ON p.proveedor_id = pr.id
            WHERE p.codigo_pos = ?
              AND p.activo = 1
            """,
            (_normalizar_texto(codigo_pos),),
        ).fetchone()


# ============================================================
# BUSCAR PRODUCTOS
# ============================================================
def obtener_producto_por_codigo(texto: str) -> Optional[Dict[str, Any]]:
    """Producto que coincide EXACTAMENTE por código de barras o por PLU.

    Devuelve None si el texto no corresponde a ningún código. Lo usa el POS
    para decidir si un Enter en el buscador viene de un lector de códigos
    (y entonces el producto se agrega directo) o si hay que buscar por
    nombre, que puede dar varios resultados.
    """
    if not texto or not str(texto).strip():
        return None
    return (obtener_producto_por_codigo_barras(texto)
            or obtener_producto_por_codigo_pos(texto))


def buscar_productos_por_nombre(texto: str) -> List[Dict[str, Any]]:
    termino = f"%{_normalizar_texto(texto)}%"

    with session_db(dict_rows=True) as conn:
        return conn.execute(
            """
            SELECT p.*,
                   c.nombre AS categoria_nombre,
                   pr.nombre AS proveedor_nombre
            FROM productos p
            LEFT JOIN categorias c ON p.categoria_id = c.id
            LEFT JOIN proveedores pr ON p.proveedor_id = pr.id
            WHERE p.activo = 1
              AND (
                    p.nombre LIKE ?
                    OR p.codigo_barras LIKE ?
                    OR p.codigo_pos LIKE ?
                    OR c.nombre LIKE ?
                    OR pr.nombre LIKE ?
                  )
            ORDER BY p.nombre ASC
            LIMIT 50
            """,
            (termino, termino, termino, termino, termino),
        ).fetchall()


def obtener_productos(activos_solo: bool = True) -> List[Dict[str, Any]]:
    condicion = "WHERE p.activo = 1" if activos_solo else ""

    with session_db(dict_rows=True) as conn:
        return conn.execute(
            f"""
            SELECT p.*,
                   c.nombre AS categoria_nombre,
                   pr.nombre AS proveedor_nombre
            FROM productos p
            LEFT JOIN categorias c ON p.categoria_id = c.id
            LEFT JOIN proveedores pr ON p.proveedor_id = pr.id
            {condicion}
            ORDER BY p.nombre ASC
            """
        ).fetchall()


def listar_productos() -> List[Dict[str, Any]]:
    return obtener_productos(activos_solo=True)