from .connection import conectar_db, session_db
from .utils import ahora
from .historial import registrar_historial


def _fila_a_dict(cursor, fila):
    columnas = [col[0] for col in cursor.description]
    return dict(zip(columnas, fila))


def abrir_caja(monto_inicial, usuario_id=None):
    monto_inicial = float(monto_inicial or 0)

    caja_abierta = obtener_caja_abierta()
    if caja_abierta:
        raise ValueError("Ya existe una caja abierta.")

    fecha = ahora()

    with session_db() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO cajas_sesiones (
                usuario_id,
                fecha_apertura,
                monto_inicial,
                estado
            )
            VALUES (?, ?, ?, 'abierta')
            """,
            (usuario_id, fecha, monto_inicial)
        )

        caja_id = cursor.lastrowid

        registrar_historial(
            accion="APERTURA_CAJA",
            tabla="cajas_sesiones",
            referencia_id=caja_id,
            detalles=f"Apertura de caja con monto inicial {monto_inicial}",
            usuario_id=usuario_id,
            conn=conn,
        )

        conn.commit()

    return obtener_caja_por_id(caja_id)


def obtener_caja_por_id(caja_id, conn=None):
    propia = conn is None
    if propia:
        conn = conectar_db(dict_rows=True)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT c.id, c.usuario_id, u.nombre AS usuario_nombre, c.fecha_apertura, c.fecha_cierre,
                   c.monto_inicial, c.monto_final_real AS monto_cierre,
                   c.estado, c.observacion
            FROM cajas_sesiones c
            LEFT JOIN usuarios u ON c.usuario_id = u.id
            WHERE c.id = ?
            """,
            (caja_id,)
        )
        fila = cursor.fetchone()
        if fila and not isinstance(fila, dict):
            return _fila_a_dict(cursor, fila)
        return fila
    finally:
        if propia:
            conn.close()


def obtener_caja_abierta(conn=None):
    propia = conn is None
    if propia:
        conn = conectar_db(dict_rows=True)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT c.id, c.usuario_id, u.nombre AS usuario_nombre, c.fecha_apertura, c.fecha_cierre,
                   c.monto_inicial, c.monto_final_real AS monto_cierre,
                   c.estado, c.observacion
            FROM cajas_sesiones c
            LEFT JOIN usuarios u ON c.usuario_id = u.id
            WHERE c.estado = 'abierta'
            ORDER BY c.id DESC
            LIMIT 1
            """
        )
        fila = cursor.fetchone()
        if fila and not isinstance(fila, dict):
            fila = _fila_a_dict(cursor, fila)
        return fila
    finally:
        if propia:
            conn.close()


def obtener_caja_abierta_por_usuario(usuario_id, conn=None):
    propia = conn is None
    if propia:
        conn = conectar_db(dict_rows=True)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, usuario_id, fecha_apertura, fecha_cierre,
                   monto_inicial, monto_final_real AS monto_cierre,
                   estado, observacion
            FROM cajas_sesiones
            WHERE estado = 'abierta' AND usuario_id IS ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (usuario_id,)
        )
        fila = cursor.fetchone()
        if fila and not isinstance(fila, dict):
            return _fila_a_dict(cursor, fila)
        return fila
    finally:
        if propia:
            conn.close()


def registrar_movimiento_caja(caja_id, tipo, monto, descripcion="", usuario_id=None,
                               referencia_id=None, referencia_tabla=None, categoria=None,
                               conn=None):
    monto = float(monto or 0)
    fecha = ahora()

    propia = conn is None
    if propia:
        conn = conectar_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO movimientos_caja (
                caja_sesion_id,
                fecha,
                tipo,
                monto,
                descripcion,
                usuario_id,
                referencia_id,
                referencia_tabla,
                categoria
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (caja_id, fecha, tipo, monto, descripcion, usuario_id,
             referencia_id, referencia_tabla, categoria)
        )

        movimiento_id = cursor.lastrowid

        registrar_historial(
            accion="MOVIMIENTO_CAJA",
            tabla="movimientos_caja",
            referencia_id=movimiento_id,
            detalles=f"{tipo} por {monto}. {descripcion}",
            usuario_id=usuario_id,
            conn=conn,
        )

        if propia:
            conn.commit()
        return movimiento_id
    finally:
        if propia:
            conn.close()


def obtener_movimientos_caja(caja_id, conn=None):
    propia = conn is None
    if propia:
        conn = conectar_db()
    try:
        # row_factory a nivel de CURSOR: no muta la conexión si fue prestada
        cursor = conn.cursor()
        cursor.row_factory = _fila_a_dict

        cursor.execute(
            """
            SELECT id, caja_sesion_id, fecha, tipo, categoria, monto, descripcion,
                   usuario_id, referencia_id, referencia_tabla
            FROM movimientos_caja
            WHERE caja_sesion_id = ?
            ORDER BY id DESC
            """,
            (caja_id,)
        )
        return cursor.fetchall()
    finally:
        if propia:
            conn.close()


def obtener_resumen_caja(caja_id):
    movimientos = obtener_movimientos_caja(caja_id)
    caja = obtener_caja_por_id(caja_id)

    if not caja:
        return None

    ingresos = 0.0
    egresos = 0.0
    ventas_efectivo = 0.0
    ventas_tarjeta = 0.0
    ventas_transferencia = 0.0

    for mov in movimientos:
        tipo = (mov.get("tipo") or "").lower()
        monto = float(mov.get("monto") or 0)

        if tipo == "ingreso":
            ingresos += monto
        elif tipo == "egreso":
            egresos += monto
        elif tipo == "venta_efectivo":
            ventas_efectivo += monto
        elif tipo == "venta_tarjeta":
            ventas_tarjeta += monto
        elif tipo == "venta_transferencia":
            ventas_transferencia += monto

    efectivo_esperado = (
        float(caja.get("monto_inicial") or 0)
        + ingresos
        + ventas_efectivo
        - egresos
    )

    res = {
        "caja": caja,
        "ventas_efectivo": ventas_efectivo,
        "ventas_tarjeta": ventas_tarjeta,
        "ventas_transferencia": ventas_transferencia,
        "ingresos": ingresos,
        "egresos": egresos,
        "efectivo_esperado": efectivo_esperado,
        "movimientos": movimientos,
    }

    return res


def cerrar_caja(caja_id, monto_cierre, usuario_id=None):
    caja = obtener_caja_por_id(caja_id)
    if not caja:
        raise ValueError("La caja no existe.")

    if caja.get("estado") != "abierta":
        raise ValueError("La caja ya está cerrada.")

    monto_cierre = float(monto_cierre or 0)
    fecha_cierre = ahora()

    with session_db() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE cajas_sesiones
            SET fecha_cierre = ?, monto_final_real = ?, estado = 'cerrada'
            WHERE id = ?
            """,
            (fecha_cierre, monto_cierre, caja_id)
        )

        registrar_historial(
            accion="CIERRE_CAJA",
            tabla="cajas_sesiones",
            referencia_id=caja_id,
            detalles=f"Cierre de caja con monto final {monto_cierre}",
            usuario_id=usuario_id,
            conn=conn,
        )

        conn.commit()

    return obtener_caja_por_id(caja_id)