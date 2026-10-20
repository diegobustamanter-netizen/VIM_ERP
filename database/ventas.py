from typing import Any, Dict, List, Optional, Tuple

from vim_logger import get_logger
from .connection import session_db
from .utils import ahora
from .historial import registrar_historial
from .caja import obtener_caja_abierta
from .finanzas_utils import obtener_config_finanzas, aplicar_redondeo


# ============================================================
# UTIL
# ============================================================

def _numero_de_folio(valor: str) -> int:
    """Extrae el correlativo de un folio 'VTA-AAAAMMDD-NNNN'. 0 si no aplica."""
    try:
        return int(str(valor).rsplit("-", 1)[1])
    except (IndexError, ValueError, TypeError):
        return 0


def generar_folio_venta(conn=None) -> str:
    """Folio correlativo por día: VTA-AAAAMMDD-NNNN.

    El formato anterior era VTA-<timestamp> con precisión de un segundo: dos
    ventas dentro del mismo segundo generaban el mismo folio y la segunda se
    rechazaba por la restricción UNIQUE de ventas.folio.

    IMPORTANTE: debe llamarse con la conexión de la transacción en curso.
    crear_venta() abre la transacción con BEGIN IMMEDIATE, que toma el
    write-lock de la base, así que entre leer el último folio e insertar la
    venta ninguna otra conexión puede colarse. Ese lock es lo que garantiza
    que el correlativo no se repita.
    """
    prefijo = f"VTA-{ahora('%Y%m%d')}"

    def _siguiente(c) -> str:
        # Solo folios del formato nuevo y del día de hoy. Los folios viejos
        # (VTA-20260819184125, sin segundo guión) no matchean y se conservan.
        fila = c.execute(
            """
            SELECT folio FROM ventas
            WHERE folio LIKE ?
            ORDER BY LENGTH(folio) DESC, folio DESC
            LIMIT 1
            """,
            (prefijo + "-%",)
        ).fetchone()

        ultimo = 0
        if fila:
            # La conexión puede venir con row_factory de dicts o de tuplas
            valor = fila["folio"] if isinstance(fila, dict) else fila[0]
            ultimo = _numero_de_folio(valor)

        return f"{prefijo}-{ultimo + 1:04d}"

    if conn is not None:
        return _siguiente(conn)

    with session_db() as c:
        return _siguiente(c)




# ============================================================
# POS COMPAT
# ============================================================

def confirmar_venta(ticket: List[Dict[str, Any]], pago_cliente: float, metodo_pago: str = "efectivo", usuario_id: Optional[int] = None) -> Tuple[bool, str, Optional[int]]:
    try:
        items = []

        for linea in ticket:
            # Para productos de peso la clave "cantidad" existe pero vale 0,
            # por lo que NO se puede usar como fallback. Se verifica tipo_venta.
            tipo_v = linea.get("tipo_venta", "unidad")
            if tipo_v == "peso":
                cantidad = float(linea.get("peso", 0))
            else:
                cantidad = float(linea.get("cantidad", 1))

            item = {
                "producto_id": int(linea["producto_id"]),
                "cantidad": cantidad,
                "descuento_linea": 0,
            }

            # Precio modificado manualmente en el POS (requiere autorización de
            # admin). Solo en ese caso se envía un precio explícito; para el
            # resto de líneas manda el precio de catálogo de la BD.
            if linea.get("precio_modificado"):
                item["precio_unitario"] = float(
                    linea.get("precio_por_kilo" if tipo_v == "peso" else "precio_unitario", 0)
                )

            items.append(item)

        venta_id = crear_venta(
            items=items,
            usuario_id=usuario_id,
            metodo_pago=metodo_pago,
            monto_pagado=float(pago_cliente),
            observacion=f"Venta POS ({metodo_pago.capitalize()})",
        )

        return True, "Venta registrada correctamente.", venta_id

    except Exception as e:
        get_logger("ventas").exception("Error al confirmar la venta")
        return False, str(e), None


# ============================================================
# CREAR VENTA
# ============================================================

def crear_venta(
    items: List[Dict[str, Any]],
    usuario_id: Optional[int],
    metodo_pago: str = "efectivo",
    monto_pagado: float = 0,
    descuento: float = 0,
    impuesto: float = 0,
    observacion: str = "",
    tipo_documento: str = "comprobante",
) -> int:

    if not items:
        raise ValueError("La venta debe incluir al menos un producto")

    # Obtener configuración financiera ANTES de la transacción
    # para no mantener el write-lock más de lo necesario
    config_fin = obtener_config_finanzas()

    with session_db(dict_rows=True) as conn:
        cursor = conn.cursor()

        # BEGIN IMMEDIATE: adquiere un write-lock de inmediato para prevenir
        # que otra conexion cierre la caja entre la validacion y el commit.
        cursor.execute("BEGIN IMMEDIATE")

        # VALIDAR CAJA ABIERTA (usa la misma conexión, solo lectura)
        caja = obtener_caja_abierta(conn=conn)
        if not caja:
            raise ValueError("No hay caja abierta")

        caja_id = caja["id"]

        subtotal = 0.0
        detalle_preparado: List[Tuple] = []
        precios_manuales: List[str] = []

        # ============================================================
        # VALIDACIÓN + CÁLCULO
        # ============================================================

        for item in items:
            producto_id = int(item["producto_id"])
            cantidad = float(item["cantidad"])
            descuento_linea = float(item.get("descuento_linea", 0))

            if cantidad <= 0:
                raise ValueError("Cantidad inválida")

            producto = conn.execute(
                """
                SELECT *
                FROM productos
                WHERE id = ?
                """,
                (producto_id,),
            ).fetchone()

            if not producto or int(producto["activo"]) != 1:
                raise ValueError(f"Producto no disponible: {producto_id}")

            tipo_item_prod = producto.get("tipo_item", "producto")
            tipo_venta = producto["tipo_venta"]

            precio_catalogo = float(
                producto["precio_por_kilo"]
                if tipo_venta == "peso"
                else producto["precio_venta"]
            )

            # Precio manual autorizado (POS). Si no viene, manda el catálogo.
            precio_manual = item.get("precio_unitario")
            if precio_manual is None:
                precio_unitario = precio_catalogo
            else:
                precio_unitario = float(precio_manual)
                if precio_unitario < 0:
                    raise ValueError(
                        f"Precio inválido para {producto['nombre']}"
                    )
                if precio_unitario != precio_catalogo:
                    precios_manuales.append(
                        f"{producto['nombre']}: {precio_catalogo} -> {precio_unitario}"
                    )

            costo_unitario = float(producto["precio_compra"])

            subtotal_linea = cantidad * precio_unitario
            total_linea = subtotal_linea - descuento_linea

            subtotal += subtotal_linea

            detalle_preparado.append(
                (
                    producto_id,
                    producto["codigo_barras"] or producto["codigo_pos"],
                    producto["nombre"],
                    tipo_venta,
                    cantidad,
                    precio_unitario,
                    costo_unitario,
                    descuento_linea,
                    subtotal_linea,
                    total_linea,
                    tipo_item_prod,
                )
            )

        # ============================================================
        # CÁLCULO DE IVA Y TOTAL
        # ============================================================
        
        # total_base es el subtotal de líneas menos descuentos generales si hubiera
        total_base = subtotal - float(descuento)
        
        # Si no se especifica impuesto, se calcula según configuración con la
        # MISMA función que usa la pantalla del POS: lo que ve el cajero es lo
        # que se cobra y se guarda.
        if float(impuesto) == 0:
            from .finanzas_utils import calcular_totales_venta
            montos = calcular_totales_venta(total_base, config_fin, metodo_pago)
            total = montos["total"]
            impuesto = montos["impuesto"]
        else:
            # Si se especifica un impuesto manual, el total es base + impuesto
            total = aplicar_redondeo(total_base + float(impuesto),
                                     config_fin["redondeo_automatico"] and metodo_pago == "efectivo")

        if float(monto_pagado) < total:
            raise ValueError("Pago insuficiente")

        vuelto = max(float(monto_pagado) - total, 0)
        # Con la conexión de la transacción: el BEGIN IMMEDIATE de arriba
        # impide que otra venta tome el mismo correlativo.
        folio = generar_folio_venta(conn)

        # ============================================================
        # INSERT VENTA
        # ============================================================

        cursor.execute(
            """
            INSERT INTO ventas (
                folio, tipo_documento, fecha, usuario_id, caja_sesion_id,
                subtotal, descuento, impuesto,
                total, monto_pagado, vuelto,
                metodo_pago, estado, observacion
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'completada', ?)
            """,
            (
                folio,
                tipo_documento,
                ahora(),
                usuario_id,
                caja_id,
                subtotal,
                float(descuento),
                float(impuesto),
                total,
                float(monto_pagado),
                vuelto,
                metodo_pago,
                observacion,
            ),
        )

        venta_id = cursor.lastrowid

        # ============================================================
        # DETALLE + INVENTARIO
        # ============================================================

        for (
            producto_id,
            codigo_producto,
            nombre_producto,
            tipo_venta,
            cantidad,
            precio_unitario,
            costo_unitario,
            descuento_linea,
            subtotal_linea,
            total_linea,
            tipo_item_prod,
        ) in detalle_preparado:

            cursor.execute(
                """
                INSERT INTO detalle_ventas (
                    venta_id, producto_id, codigo_producto, nombre_producto,
                    tipo_venta, cantidad, precio_unitario, costo_unitario,
                    descuento_linea, subtotal_linea, total_linea
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    venta_id,
                    producto_id,
                    codigo_producto,
                    nombre_producto,
                    tipo_venta,
                    cantidad,
                    precio_unitario,
                    costo_unitario,
                    descuento_linea,
                    subtotal_linea,
                    total_linea,
                ),
            )

            if tipo_item_prod != "servicio":
                # Actualización atómica: solo descuenta si hay stock suficiente
                result = conn.execute(
                    """
                    UPDATE productos 
                    SET stock = stock - ?, fecha_actualizacion = ?
                    WHERE id = ? AND stock >= ?
                    """,
                    (cantidad, ahora(), producto_id, cantidad),
                )
                if result.rowcount == 0:
                    raise ValueError(f"Stock insuficiente para {nombre_producto}")

                # Obtener el stock resultante
                nuevo_stock = conn.execute(
                    "SELECT stock FROM productos WHERE id = ?",
                    (producto_id,),
                ).fetchone()["stock"]

                conn.execute(
                    """
                    INSERT INTO movimientos_inventario (
                        fecha, producto_id, tipo_movimiento, cantidad,
                        stock_anterior, stock_nuevo,
                        referencia_id, referencia_tabla, usuario_id, motivo
                    )
                    VALUES (?, ?, 'venta', ?, ?, ?, ?, 'ventas', ?, ?)
                    """,
                    (
                        ahora(),
                        producto_id,
                        -cantidad,
                        nuevo_stock + cantidad,
                        nuevo_stock,
                        venta_id,
                        usuario_id,
                        f"Venta {folio}",
                    ),
                )

        # ============================================================
        # CAJA (TODOS LOS METODOS)
        # ============================================================

        tipo_movimiento = f"venta_{metodo_pago}"
        conn.execute(
            """
            INSERT INTO movimientos_caja (
                caja_sesion_id, fecha, tipo, categoria, monto,
                descripcion, usuario_id, referencia_id, referencia_tabla
            )
            VALUES (?, ?, ?, 'venta', ?, ?, ?, ?, 'ventas')
            """,
            (
                caja_id,
                ahora(),
                tipo_movimiento,
                total,
                f"Venta {folio} ({metodo_pago.capitalize()})",
                usuario_id,
                venta_id,
            ),
        )

        conn.commit()

    # ============================================================
    # HISTORIAL
    # ============================================================

    detalle_historial = f"Venta {folio} total: {total}"
    if precios_manuales:
        detalle_historial += " | Precios modificados: " + "; ".join(precios_manuales)

    registrar_historial(
        "crear_venta",
        "ventas",
        venta_id,
        detalle_historial,
        usuario_id
    )

    return venta_id


# ============================================================
# CONSULTA
# ============================================================

def resumen_ventas_periodo(fecha_inicio: str, fecha_fin: str) -> Dict[str, Any]:
    """Cuántas ventas y cuánto suman en un período, sin traer las filas.

    Lo usa el Centro de Descargas para mostrar qué se va a exportar antes de
    pedir dónde guardar. Es un COUNT/SUM, no la consulta completa: puede
    correr cada vez que el usuario cambia el período sin que se note.
    """
    try:
        with session_db(dict_rows=True) as conn:
            fila = conn.execute(
                """
                SELECT COUNT(*) AS cantidad,
                       COALESCE(SUM(total), 0) AS total
                FROM ventas
                WHERE fecha >= ? AND fecha < date(?, '+1 day')
                  AND estado != 'anulada'
                """,
                (fecha_inicio, fecha_fin)
            ).fetchone()
            return {"cantidad": fila["cantidad"] or 0, "total": fila["total"] or 0}
    except Exception as e:
        from vim_logger import get_logger
        get_logger("ventas.resumen").warning(
            f"No se pudo resumir el período {fecha_inicio}..{fecha_fin}: {e}"
        )
        return {"cantidad": 0, "total": 0}


def obtener_folio_venta(venta_id: int) -> str:
    """Folio real de una venta. Cadena vacía si no se encuentra."""
    try:
        with session_db(dict_rows=True) as conn:
            fila = conn.execute(
                "SELECT folio FROM ventas WHERE id = ?", (venta_id,)
            ).fetchone()
            return (fila["folio"] or "") if fila else ""
    except Exception:
        get_logger("ventas").exception("No se pudo leer el folio de la venta %s", venta_id)
        return ""


def obtener_venta_por_id(venta_id: int) -> Optional[Dict[str, Any]]:
    with session_db(dict_rows=True) as conn:
        venta = conn.execute(
            """
            SELECT v.*, u.nombre AS usuario_nombre
            FROM ventas v
            LEFT JOIN usuarios u ON u.id = v.usuario_id
            WHERE v.id = ?
            """,
            (venta_id,),
        ).fetchone()

        if not venta:
            return None

        detalles = conn.execute(
            """
            SELECT *
            FROM detalle_ventas
            WHERE venta_id = ?
            ORDER BY id ASC
            """,
            (venta_id,),
        ).fetchall()

        venta["detalles"] = detalles
        return venta


def buscar_ventas_filtradas(
    fecha_desde: str = "",
    fecha_hasta: str = "",
    metodo_pago: str = "",
    busqueda_folio: str = "",
    limit: int = 0,
    offset: int = 0
) -> List[Dict[str, Any]]:
    query = """
        SELECT v.*, u.nombre AS usuario_nombre
        FROM ventas v
        LEFT JOIN usuarios u ON u.id = v.usuario_id
        WHERE v.estado IN ('completada', 'anulada')
    """
    params = []

    if fecha_desde:
        query += " AND v.fecha >= ?"
        params.append(fecha_desde)
    
    if fecha_hasta:
        query += " AND v.fecha < date(?, '+1 day')"
        params.append(fecha_hasta)
        
    if metodo_pago and metodo_pago.lower() != "todos":
        query += " AND v.metodo_pago = ?"
        params.append(metodo_pago.lower())
        
    if busqueda_folio:
        query += " AND v.folio LIKE ?"
        params.append(f"%{busqueda_folio}%")

    query += " ORDER BY v.fecha DESC"
    if limit:
        query += " LIMIT ?"
        params.append(limit)
        if offset:
            query += " OFFSET ?"
            params.append(offset)

    with session_db(dict_rows=True) as conn:
        return conn.execute(query, params).fetchall()


def contar_ventas_filtradas(
    fecha_desde: str = "",
    fecha_hasta: str = "",
    metodo_pago: str = "",
    busqueda_folio: str = ""
) -> int:
    query = """
        SELECT COUNT(v.id) as total
        FROM ventas v
        WHERE v.estado IN ('completada', 'anulada')
    """
    params = []

    if fecha_desde:
        query += " AND v.fecha >= ?"
        params.append(fecha_desde)
    
    if fecha_hasta:
        query += " AND v.fecha < date(?, '+1 day')"
        params.append(fecha_hasta)
        
    if metodo_pago and metodo_pago.lower() != "todos":
        query += " AND v.metodo_pago = ?"
        params.append(metodo_pago.lower())
        
    if busqueda_folio:
        query += " AND v.folio LIKE ?"
        params.append(f"%{busqueda_folio}%")

    with session_db(dict_rows=True) as conn:
        row = conn.execute(query, params).fetchone()
        return int(row["total"] or 0)


def obtener_kpis_ventas(
    fecha_desde: str = "",
    fecha_hasta: str = "",
    metodo_pago: str = "",
    busqueda_folio: str = ""
) -> Dict[str, Any]:
    # Corregimos la consulta: Agrupamos la utilidad por venta en una subconsulta
    # para evitar que el JOIN multiplique los totales de la tabla 'ventas'
    query = """
        SELECT 
            COUNT(v.id) as cantidad_ventas,
            SUM(v.total) as ventas_totales,
            SUM(v.total - v.impuesto) as ventas_netas,
            SUM(CASE WHEN v.metodo_pago = 'efectivo' THEN v.total ELSE 0 END) as total_efectivo,
            SUM(CASE WHEN v.metodo_pago = 'tarjeta' THEN v.total ELSE 0 END) as total_tarjeta,
            SUM(CASE WHEN v.metodo_pago = 'transferencia' THEN v.total ELSE 0 END) as total_transferencia,
            SUM(u.utilidad_venta) as utilidad_total
        FROM ventas v
        LEFT JOIN (
            SELECT venta_id, SUM(total_linea - (cantidad * costo_unitario)) as utilidad_venta
            FROM detalle_ventas
            GROUP BY venta_id
        ) u ON v.id = u.venta_id
        WHERE v.estado = 'completada'
    """
    params = []

    if fecha_desde:
        query += " AND v.fecha >= ?"
        params.append(fecha_desde)
    
    if fecha_hasta:
        query += " AND v.fecha < date(?, '+1 day')"
        params.append(fecha_hasta)
        
    if metodo_pago and metodo_pago.lower() != "todos":
        query += " AND v.metodo_pago = ?"
        params.append(metodo_pago.lower())
        
    if busqueda_folio:
        query += " AND folio LIKE ?"
        params.append(f"%{busqueda_folio}%")

    with session_db(dict_rows=True) as conn:
        row = conn.execute(query, params).fetchone()
        
    cantidad = row["cantidad_ventas"] or 0
    ventas_totales = row["ventas_totales"] or 0.0
    ticket_promedio = ventas_totales / cantidad if cantidad > 0 else 0.0

    return {
        "cantidad_ventas": cantidad,
        "ventas_totales": ventas_totales,
        "ventas_netas": row["ventas_netas"] or 0.0,
        "ticket_promedio": ticket_promedio,
        "total_efectivo": row["total_efectivo"] or 0.0,
        "total_tarjeta": row["total_tarjeta"] or 0.0,
        "total_transferencia": row["total_transferencia"] or 0.0,
        "utilidad_total": row["utilidad_total"] or 0.0,
    }



def obtener_reportes_avanzados(
    fecha_desde: str = "",
    fecha_hasta: str = "",
    metodo_pago: str = "",
    busqueda_folio: str = ""
) -> Dict[str, Any]:
    
    filtro_ventas = "v.estado = 'completada'"
    params_ventas = []
    
    if fecha_desde:
        filtro_ventas += " AND v.fecha >= ?"
        params_ventas.append(fecha_desde)
    if fecha_hasta:
        filtro_ventas += " AND v.fecha < date(?, '+1 day')"
        params_ventas.append(fecha_hasta)
    if metodo_pago and metodo_pago.lower() != "todos":
        filtro_ventas += " AND v.metodo_pago = ?"
        params_ventas.append(metodo_pago.lower())
    if busqueda_folio:
        filtro_ventas += " AND v.folio LIKE ?"
        params_ventas.append(f"%{busqueda_folio}%")

    query_prod = f"""
        SELECT 
            dv.nombre_producto,
            SUM(dv.cantidad) as cantidad_total,
            SUM(dv.total_linea) as ingresos_totales,
            SUM(dv.total_linea - (dv.cantidad * dv.costo_unitario)) as utilidad_total
        FROM detalle_ventas dv
        JOIN ventas v ON v.id = dv.venta_id
        WHERE {filtro_ventas}
        GROUP BY dv.producto_id, dv.nombre_producto
        ORDER BY ingresos_totales DESC
        LIMIT 20
    """

    query_cat = f"""
        SELECT 
            COALESCE(c.nombre, 'Sin Categoría') as categoria,
            SUM(dv.cantidad) as cantidad_total,
            SUM(dv.total_linea) as ingresos_totales,
            SUM(dv.total_linea - (dv.cantidad * dv.costo_unitario)) as utilidad_total
        FROM detalle_ventas dv
        JOIN ventas v ON v.id = dv.venta_id
        JOIN productos p ON p.id = dv.producto_id
        LEFT JOIN categorias c ON c.id = p.categoria_id
        WHERE {filtro_ventas}
        GROUP BY p.categoria_id, c.nombre
        ORDER BY ingresos_totales DESC
        LIMIT 15
    """

    query_hora = f"""
        SELECT 
            strftime('%H', v.fecha) || ':00' as hora,
            COUNT(v.id) as tickets,
            SUM(v.total) as ingresos_totales
        FROM ventas v
        WHERE {filtro_ventas} AND v.fecha IS NOT NULL
        GROUP BY strftime('%H', v.fecha)
        ORDER BY strftime('%H', v.fecha) ASC
    """

    query_dia = f"""
        SELECT 
            date(v.fecha) as dia,
            COUNT(v.id) as tickets,
            SUM(v.total) as ingresos_totales
        FROM ventas v
        WHERE {filtro_ventas} AND v.fecha IS NOT NULL
        GROUP BY date(v.fecha)
        ORDER BY date(v.fecha) ASC
    """

    with session_db(dict_rows=True) as conn:
        top_productos = conn.execute(query_prod, params_ventas).fetchall()
        top_categorias = conn.execute(query_cat, params_ventas).fetchall()
        ventas_hora = conn.execute(query_hora, params_ventas).fetchall()
        ventas_dia = conn.execute(query_dia, params_ventas).fetchall()

    return {
        "top_productos": top_productos,
        "top_categorias": top_categorias,
        "ventas_por_hora": ventas_hora,
        "ventas_por_dia": ventas_dia,
    }


def anular_venta(venta_id: int, usuario_id: Optional[int], motivo: str = "Anulación administrativa") -> Tuple[bool, str]:
    """Anula una venta, revierte el stock y registra el movimiento de reversión.

    Todo ocurre en una sola transacción con BEGIN IMMEDIATE: si dos anulaciones
    de la misma venta llegan a la vez, la segunda espera y encuentra la venta
    ya anulada, así el stock nunca se devuelve dos veces.

    El dinero devuelto sale de la caja de la venta si sigue abierta; si ya se
    cerró, sale de la caja abierta ahora. Si no hay ninguna abierta, no se anula.
    """
    folio = None
    try:
        with session_db(dict_rows=True) as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE")

            # 1. Obtener la venta (dentro del lock: el estado ya no puede cambiar)
            venta = cursor.execute("SELECT * FROM ventas WHERE id = ? AND estado = 'completada'", (venta_id,)).fetchone()
            if not venta:
                return False, "La venta no existe o ya ha sido anulada."
            folio = venta["folio"]

            # 2. Caja de donde sale el dinero devuelto
            caja_venta = cursor.execute(
                "SELECT id, estado FROM cajas_sesiones WHERE id = ?",
                (venta["caja_sesion_id"],),
            ).fetchone()
            if caja_venta and caja_venta["estado"] == "abierta":
                caja_sesion_id = caja_venta["id"]
            else:
                caja_actual = obtener_caja_abierta(conn=conn)
                if not caja_actual:
                    return False, "No hay caja abierta. Abre la caja antes de anular la venta."
                caja_sesion_id = caja_actual["id"]

            # 3. Obtener detalles para revertir stock
            detalles = cursor.execute("SELECT * FROM detalle_ventas WHERE venta_id = ?", (venta_id,)).fetchall()

            for d in detalles:
                pid = d["producto_id"]
                cant = d["cantidad"]

                prod = cursor.execute("SELECT tipo_item FROM productos WHERE id = ?", (pid,)).fetchone()
                if prod and prod["tipo_item"] == "servicio":
                    continue

                # Revertir stock en tabla productos
                cursor.execute("UPDATE productos SET stock = stock + ?, fecha_actualizacion = ? WHERE id = ?", (cant, ahora(), pid))

                # Registrar movimiento de inventario (Entrada por anulación)
                cursor.execute("""
                    INSERT INTO movimientos_inventario (
                        fecha, producto_id, tipo_movimiento, cantidad,
                        stock_anterior, stock_nuevo,
                        referencia_id, referencia_tabla, usuario_id, motivo
                    )
                    SELECT ?, ?, 'entrada', ?, stock - ?, stock, ?, 'ventas', ?, ?
                    FROM productos WHERE id = ?
                """, (ahora(), pid, cant, cant, venta_id, usuario_id, f"Anulación Venta {folio}: {motivo}", pid))

            # 4. Revertir movimiento en caja
            # Solo una venta en efectivo devuelve billetes del cajón (egreso).
            # Una con tarjeta o transferencia se descuenta de su propio medio:
            # antes todas salían como egreso y el "efectivo esperado" de la
            # caja quedaba corto por plata que nunca entró al cajón.
            metodo = str(venta["metodo_pago"] or "efectivo").lower()
            if metodo in ("tarjeta", "transferencia"):
                tipo_mov, monto_mov = f"venta_{metodo}", -abs(venta["total"])
            else:
                tipo_mov, monto_mov = "egreso", abs(venta["total"])
            cursor.execute("""
                INSERT INTO movimientos_caja (
                    caja_sesion_id, fecha, tipo, categoria, monto,
                    descripcion, usuario_id, referencia_id, referencia_tabla
                )
                VALUES (?, ?, ?, 'anulación', ?, ?, ?, ?, 'ventas')
            """, (caja_sesion_id, ahora(), tipo_mov, monto_mov, f"Anulación {folio}: {motivo}", usuario_id, venta_id))

            # 5. Cambiar estado de la venta
            cursor.execute("UPDATE ventas SET estado = 'anulada', observacion = ? WHERE id = ?", (f"ANULADA: {motivo}", venta_id))
            # El commit lo hace session_db al salir del bloque.

        registrar_historial("anular_venta", "ventas", venta_id, f"Venta {folio} anulada: {motivo}", usuario_id)
        return True, f"Venta {folio} anulada con éxito."

    except Exception as e:
        get_logger("ventas").exception("Error al anular la venta %s (folio %s)", venta_id, folio)
        return False, f"Error al anular venta: {str(e)}"
