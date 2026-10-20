from typing import Any, Dict, List, Optional
from .connection import session_db
from .utils import ahora
from .historial import registrar_historial
from .caja import registrar_movimiento_caja, obtener_caja_abierta

def registrar_compra_erp(
    tipo_operacion: str,  # 'compra_inventario', 'gasto_operativo', 'sueldos', 'activo_fijo'
    proveedor_id: Optional[int],
    numero_documento: str,
    total: float,
    cuenta_contable_id: int,
    estado_pago: str = 'pagado',  # 'pendiente', 'parcial', 'pagado'
    subtotal: float = 0,
    descuento: float = 0,
    impuesto: float = 0,
    items: List[Dict[str, Any]] = None,
    usuario_id: Optional[int] = None,
    observacion: str = "",
    tipo_documento: str = "factura",
    fecha: Optional[str] = None   # fecha del documento en formato AAAA-MM-DD
) -> int:
    """
    Registra una compra o gasto en el sistema ERP.
    """
    fecha = fecha if fecha else ahora()

    saldo_pendiente = total if estado_pago == 'pendiente' else 0

    with session_db() as conn:
        cursor = conn.cursor()
        
        # 1. Insertar la cabecera de la compra
        cursor.execute(
            """
            INSERT INTO compras (
                numero_documento, tipo_documento, fecha, proveedor_id, usuario_id,
                subtotal, descuento, impuesto, total,
                tipo_operacion, estado_pago, saldo_pendiente, cuenta_contable_id,
                estado, observacion
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'registrada', ?)
            """,
            (
                numero_documento, tipo_documento, fecha, proveedor_id, usuario_id,
                subtotal, descuento, impuesto, total,
                tipo_operacion, estado_pago, saldo_pendiente, cuenta_contable_id,
                observacion
            )
        )
        compra_id = cursor.lastrowid

        # 2. Insertar detalles si existen
        if items:
            for item in items:
                cursor.execute(
                    """
                    INSERT INTO detalle_compras (
                        compra_id, producto_id, codigo_producto, nombre_producto,
                        cantidad, costo_unitario, subtotal_linea
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        compra_id, 
                        item.get('producto_id'), 
                        item.get('codigo'), 
                        item.get('nombre'),
                        item.get('cantidad', 0), 
                        item.get('costo', 0), 
                        item.get('total_linea', 0)
                    )
                )
                
                if tipo_operacion == 'compra_inventario' and item.get('producto_id'):
                    cursor.execute("SELECT tipo_item FROM productos WHERE id = ?", (item.get('producto_id'),))
                    prod_info = cursor.fetchone()
                    if prod_info and prod_info[0] != 'servicio':
                        cursor.execute(
                            "UPDATE productos SET stock = stock + ? WHERE id = ?",
                            (item.get('cantidad', 0), item.get('producto_id'))
                        )
                        cursor.execute(
                            """
                            INSERT INTO movimientos_inventario (
                                fecha, producto_id, tipo_movimiento, cantidad,
                                stock_anterior, stock_nuevo, referencia_id, referencia_tabla,
                                usuario_id, motivo
                            )
                            SELECT ?, ?, 'compra', ?, stock - ?, stock, ?, 'compras', ?, ?
                            FROM productos WHERE id = ?
                            """,
                            (
                                fecha, item.get('producto_id'), item.get('cantidad'), 
                                item.get('cantidad'), compra_id, usuario_id, f"Compra {numero_documento}",
                                item.get('producto_id')
                            )
                        )

        # 4. Pago contado
        if estado_pago == 'pagado':
            caja = obtener_caja_abierta(conn=conn)
            if caja:
                registrar_movimiento_caja(
                    caja_id=caja['id'],
                    tipo='egreso',
                    monto=total,
                    descripcion=f"Pago Contado {tipo_operacion.replace('_', ' ').title()}: {numero_documento}",
                    usuario_id=usuario_id,
                    referencia_id=compra_id,
                    referencia_tabla='compras',
                    conn=conn
                )

        registrar_historial(
            accion="REGISTRO_COMPRA_ERP",
            tabla="compras",
            referencia_id=compra_id,
            detalles=f"Registro de {tipo_operacion} por {total}. Docto: {numero_documento}",
            usuario_id=usuario_id,
            conn=conn
        )
        return compra_id

def registrar_pago_documento(
    compra_id: int,
    monto: float,
    metodo_pago: str = 'efectivo',
    referencia_pago: str = "",
    usuario_id: Optional[int] = None
) -> int:
    monto = float(monto or 0)
    if monto <= 0:
        raise ValueError("El monto del pago debe ser mayor a cero.")

    fecha = ahora()
    with session_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT total, saldo_pendiente, numero_documento FROM compras WHERE id = ?", (compra_id,))
        compra = cursor.fetchone()
        if not compra:
            raise ValueError("Documento no encontrado.")

        total_docto, saldo_actual, num_doc = compra
        if monto > float(saldo_actual or 0):
            raise ValueError(
                f"El pago (${monto:,.0f}) supera el saldo pendiente (${saldo_actual:,.0f})."
            )
        caja = obtener_caja_abierta(conn=conn)
        caja_id = caja['id'] if caja else None
        
        cursor.execute(
            """
            INSERT INTO pagos_documentos (compra_id, fecha, monto, metodo_pago, caja_sesion_id, referencia_pago)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (compra_id, fecha, monto, metodo_pago, caja_id, referencia_pago)
        )
        pago_id = cursor.lastrowid
        
        nuevo_saldo = saldo_actual - monto
        nuevo_estado = 'pagado' if nuevo_saldo <= 0 else 'parcial'
        
        cursor.execute(
            "UPDATE compras SET saldo_pendiente = ?, estado_pago = ? WHERE id = ?",
            (max(0, nuevo_saldo), nuevo_estado, compra_id)
        )
        
        if caja:
            registrar_movimiento_caja(
                caja_id=caja_id,
                tipo='egreso',
                monto=monto,
                descripcion=f"Abono a Docto {num_doc} ({metodo_pago})",
                usuario_id=usuario_id,
                referencia_id=pago_id,
                referencia_tabla='pagos_documentos',
                conn=conn
            )
            
        return pago_id

def obtener_compras_pendientes() -> List[Dict[str, Any]]:
    with session_db(dict_rows=True) as conn:
        return conn.execute(
            """
            SELECT c.*, p.nombre as nombre_proveedor, pc.nombre as nombre_cuenta
            FROM compras c
            LEFT JOIN proveedores p ON c.proveedor_id = p.id
            LEFT JOIN plan_cuentas pc ON c.cuenta_contable_id = pc.id
            WHERE c.estado_pago != 'pagado' AND c.estado != 'anulada'
            ORDER BY c.fecha ASC
            """
        ).fetchall()

def anular_compra(compra_id: int, usuario_id: Optional[int] = None) -> bool:
    with session_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT tipo_operacion, estado, total, estado_pago, numero_documento FROM compras WHERE id = ?", (compra_id,))
        compra = cursor.fetchone()
        if not compra or compra[1] == 'anulada':
            return False
            
        tipo_op, estado, total, estado_pago, num_doc = compra
        
        if tipo_op == 'compra_inventario':
            cursor.execute("SELECT producto_id, cantidad FROM detalle_compras WHERE compra_id = ?", (compra_id,))
            detalles = cursor.fetchall()
            for prod_id, cant in detalles:
                if prod_id:
                    cursor.execute("SELECT tipo_item FROM productos WHERE id = ?", (prod_id,))
                    prod_info = cursor.fetchone()
                    if prod_info and prod_info[0] != 'servicio':
                        cursor.execute("UPDATE productos SET stock = stock - ? WHERE id = ?", (cant, prod_id))
                        cursor.execute(
                            """
                            INSERT INTO movimientos_inventario (
                                fecha, producto_id, tipo_movimiento, cantidad,
                                stock_anterior, stock_nuevo, referencia_id, referencia_tabla,
                                usuario_id, motivo
                            )
                            SELECT ?, ?, 'anulacion_compra', ?, stock + ?, stock, ?, 'compras', ?, ?
                            FROM productos WHERE id = ?
                            """,
                            (ahora(), prod_id, -cant, cant, compra_id, usuario_id, f"Anulación Compra {num_doc}", prod_id)
                        )

        # 2. Revertir movimientos de caja (Pago inicial y Abonos posteriores)
        # NOTA: los paréntesis alrededor del OR son necesarios. Sin ellos,
        # AND liga más fuerte que OR y el filtro tipo='egreso' no se aplicaba
        # a la primera rama, pudiendo revertir movimientos equivocados.
        cursor.execute(
            """
            SELECT id, monto, caja_sesion_id, referencia_tabla
            FROM movimientos_caja
            WHERE (
                    (referencia_id = ? AND referencia_tabla = 'compras')
                 OR (referencia_tabla = 'pagos_documentos' AND referencia_id IN (SELECT id FROM pagos_documentos WHERE compra_id = ?))
                  )
              AND tipo = 'egreso'
            """,
            (compra_id, compra_id)
        )
        movs = cursor.fetchall()
        for mov_id, monto, caja_id, ref_tabla in movs:
            registrar_movimiento_caja(
                caja_id=caja_id,
                tipo='ingreso',
                monto=monto,
                descripcion=f"REVERSA ({ref_tabla.replace('_', ' ').title()}): Anulación Docto {num_doc}",
                usuario_id=usuario_id,
                referencia_id=mov_id,
                referencia_tabla=ref_tabla,
                conn=conn
            )

        cursor.execute(
            "UPDATE compras SET estado = 'anulada', saldo_pendiente = 0, estado_pago = 'anulado' WHERE id = ?",
            (compra_id,)
        )
        
        registrar_historial(
            accion="ANULAR_COMPRA",
            tabla="compras",
            referencia_id=compra_id,
            detalles=f"Anulación de documento {num_doc}. Monto {total}",
            usuario_id=usuario_id,
            conn=conn
        )
        return True
