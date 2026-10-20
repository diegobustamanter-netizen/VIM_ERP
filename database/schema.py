from .connection import session_db
from .seed import insertar_datos_base


def inicializar_db() -> None:
    with session_db() as conn:
        cursor = conn.cursor()

        # ============================================================
        # TABLAS MAESTRAS
        # ============================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS categorias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE,
                descripcion TEXT,
                activa INTEGER NOT NULL DEFAULT 1,
                fecha_creacion TEXT NOT NULL,
                fecha_actualizacion TEXT
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS proveedores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE,
                rut TEXT,
                telefono TEXT,
                email TEXT,
                direccion TEXT,
                contacto TEXT,
                activo INTEGER NOT NULL DEFAULT 1,
                fecha_creacion TEXT NOT NULL,
                fecha_actualizacion TEXT
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                nombre TEXT NOT NULL,
                rol TEXT NOT NULL DEFAULT 'cajero',
                activo INTEGER NOT NULL DEFAULT 1,
                fecha_creacion TEXT NOT NULL,
                ultimo_acceso TEXT,
                pregunta_seguridad TEXT,
                respuesta_hash TEXT
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS permisos_modulo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                modulo TEXT NOT NULL,
                permitido INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
                UNIQUE(usuario_id, modulo)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo_barras TEXT UNIQUE,
                codigo_pos TEXT UNIQUE,
                nombre TEXT NOT NULL,
                descripcion TEXT,
                tipo_item VARCHAR(50) NOT NULL DEFAULT 'producto',
                categoria_id INTEGER,
                proveedor_id INTEGER,
                precio_compra REAL NOT NULL DEFAULT 0,
                precio_venta REAL NOT NULL DEFAULT 0,
                precio_por_kilo REAL NOT NULL DEFAULT 0,
                stock REAL NOT NULL DEFAULT 0,
                stock_minimo REAL NOT NULL DEFAULT 0,
                unidad_medida TEXT NOT NULL DEFAULT 'unidad',
                tipo_venta TEXT NOT NULL DEFAULT 'unidad',
                permite_descuento INTEGER NOT NULL DEFAULT 1,
                activo INTEGER NOT NULL DEFAULT 1,
                fecha_creacion TEXT NOT NULL,
                fecha_actualizacion TEXT,
                FOREIGN KEY (categoria_id) REFERENCES categorias(id) ON DELETE SET NULL,
                FOREIGN KEY (proveedor_id) REFERENCES proveedores(id) ON DELETE SET NULL
            )
            """
        )

        # ============================================================
        # CAJA
        # ============================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cajas_sesiones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER,
                fecha_apertura TEXT NOT NULL,
                fecha_cierre TEXT,
                monto_inicial REAL NOT NULL DEFAULT 0,
                monto_final_esperado REAL NOT NULL DEFAULT 0,
                monto_final_real REAL,
                diferencia REAL NOT NULL DEFAULT 0,
                estado TEXT NOT NULL DEFAULT 'abierta',
                observacion TEXT,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS movimientos_caja (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                caja_sesion_id INTEGER NOT NULL,
                fecha TEXT NOT NULL,
                tipo TEXT NOT NULL,                -- ingreso / egreso
                categoria TEXT,                    -- sencillo / retiro / gasto / ajuste
                monto REAL NOT NULL,
                descripcion TEXT,
                usuario_id INTEGER,
                referencia_id INTEGER,
                referencia_tabla TEXT,
                FOREIGN KEY (caja_sesion_id) REFERENCES cajas_sesiones(id) ON DELETE CASCADE,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
            )
            """
        )

        # ============================================================
        # VENTAS
        # ============================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ventas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                folio TEXT UNIQUE,
                tipo_documento TEXT NOT NULL DEFAULT 'comprobante',
                fecha TEXT NOT NULL,
                usuario_id INTEGER,
                caja_sesion_id INTEGER,
                subtotal REAL NOT NULL DEFAULT 0,
                descuento REAL NOT NULL DEFAULT 0,
                impuesto REAL NOT NULL DEFAULT 0,
                total REAL NOT NULL DEFAULT 0,
                monto_pagado REAL NOT NULL DEFAULT 0,
                vuelto REAL NOT NULL DEFAULT 0,
                metodo_pago TEXT NOT NULL DEFAULT 'efectivo',
                estado TEXT NOT NULL DEFAULT 'completada',
                observacion TEXT,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL,
                FOREIGN KEY (caja_sesion_id) REFERENCES cajas_sesiones(id) ON DELETE SET NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS detalle_ventas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                venta_id INTEGER NOT NULL,
                producto_id INTEGER,
                codigo_producto TEXT,
                nombre_producto TEXT NOT NULL,
                tipo_venta TEXT NOT NULL DEFAULT 'unidad',
                cantidad REAL NOT NULL DEFAULT 0,
                precio_unitario REAL NOT NULL DEFAULT 0,
                costo_unitario REAL NOT NULL DEFAULT 0,
                descuento_linea REAL NOT NULL DEFAULT 0,
                subtotal_linea REAL NOT NULL DEFAULT 0,
                total_linea REAL NOT NULL DEFAULT 0,
                FOREIGN KEY (venta_id) REFERENCES ventas(id) ON DELETE CASCADE,
                FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE SET NULL
            )
            """
        )

        # ============================================================
        # COMPRAS
        # ============================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS compras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_documento TEXT,
                tipo_documento TEXT NOT NULL DEFAULT 'factura',
                fecha TEXT NOT NULL,
                proveedor_id INTEGER,
                usuario_id INTEGER,
                subtotal REAL NOT NULL DEFAULT 0,
                descuento REAL NOT NULL DEFAULT 0,
                impuesto REAL NOT NULL DEFAULT 0,
                total REAL NOT NULL DEFAULT 0,
                tipo_operacion TEXT NOT NULL DEFAULT 'compra_inventario', -- compra_inventario, gasto_operativo, sueldos, activo_fijo
                estado_pago TEXT NOT NULL DEFAULT 'pagado',               -- pendiente, parcial, pagado
                saldo_pendiente REAL NOT NULL DEFAULT 0,
                cuenta_contable_id INTEGER,
                estado TEXT NOT NULL DEFAULT 'registrada',
                observacion TEXT,
                FOREIGN KEY (proveedor_id) REFERENCES proveedores(id) ON DELETE SET NULL,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL,
                FOREIGN KEY (cuenta_contable_id) REFERENCES plan_cuentas(id) ON DELETE SET NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS detalle_compras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                compra_id INTEGER NOT NULL,
                producto_id INTEGER,
                codigo_producto TEXT,
                nombre_producto TEXT NOT NULL,
                cantidad REAL NOT NULL DEFAULT 0,
                costo_unitario REAL NOT NULL DEFAULT 0,
                subtotal_linea REAL NOT NULL DEFAULT 0,
                FOREIGN KEY (compra_id) REFERENCES compras(id) ON DELETE CASCADE,
                FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE SET NULL
            )
            """
        )

        # ============================================================
        # ERP - FINANZAS Y PERSONAL
        # ============================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS empleados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rut TEXT UNIQUE,
                nombre TEXT NOT NULL,
                cargo TEXT,
                sueldo_base REAL NOT NULL DEFAULT 0,
                activo INTEGER NOT NULL DEFAULT 1,
                fecha_ingreso TEXT NOT NULL,
                fecha_termino TEXT,
                email TEXT,
                telefono TEXT
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS liquidaciones_sueldo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empleado_id INTEGER NOT NULL,
                periodo TEXT NOT NULL,               -- formato AAAA-MM ej: 2026-04
                sueldo_base REAL NOT NULL DEFAULT 0,
                bonos REAL NOT NULL DEFAULT 0,
                descuentos REAL NOT NULL DEFAULT 0,
                total_liquido REAL NOT NULL DEFAULT 0,
                fecha_pago TEXT NOT NULL,
                estado TEXT NOT NULL DEFAULT 'pagado', -- pagado, anulada
                observacion TEXT,
                FOREIGN KEY (empleado_id) REFERENCES empleados(id) ON DELETE CASCADE,
                UNIQUE(empleado_id, periodo)          -- un pago por empleado por período
            )
            """
        )


        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS plan_cuentas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT UNIQUE NOT NULL,
                nombre TEXT NOT NULL,
                tipo TEXT NOT NULL,                -- activo, pasivo, patrimonio, ingreso, egreso
                es_inventariable INTEGER NOT NULL DEFAULT 0,
                activo INTEGER NOT NULL DEFAULT 1
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS pagos_documentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                compra_id INTEGER NOT NULL,
                fecha TEXT NOT NULL,
                monto REAL NOT NULL,
                metodo_pago TEXT NOT NULL DEFAULT 'efectivo',
                caja_sesion_id INTEGER,
                referencia_pago TEXT,
                FOREIGN KEY (compra_id) REFERENCES compras(id) ON DELETE CASCADE,
                FOREIGN KEY (caja_sesion_id) REFERENCES cajas_sesiones(id) ON DELETE SET NULL
            )
            """
        )

        # ============================================================
        # INVENTARIO / HISTORIAL / CONFIG
        # ============================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS movimientos_inventario (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                producto_id INTEGER NOT NULL,
                tipo_movimiento TEXT NOT NULL,
                cantidad REAL NOT NULL,
                stock_anterior REAL NOT NULL,
                stock_nuevo REAL NOT NULL,
                referencia_id INTEGER,
                referencia_tabla TEXT,
                usuario_id INTEGER,
                motivo TEXT,
                FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS historial (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                accion TEXT NOT NULL,
                tabla TEXT,
                referencia_id INTEGER,
                detalles TEXT,
                usuario_id INTEGER,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS configuracion (
                clave TEXT PRIMARY KEY,
                valor TEXT,
                descripcion TEXT
            )
            """
        )

        # ============================================================
        # MIGRACIONES SEGURAS PARA BASES EXISTENTES
        # ============================================================

        _agregar_columna_si_no_existe(cursor, "ventas", "caja_sesion_id", "INTEGER")
        _agregar_columna_si_no_existe(cursor, "ventas", "tipo_documento", "TEXT NOT NULL DEFAULT 'comprobante'")
        # VIM ERP no emite boletas del SII: lo que entrega es un comprobante
        # interno. Las ventas viejas quedaron marcadas como 'boleta' por error.
        cursor.execute("UPDATE ventas SET tipo_documento = 'comprobante' WHERE tipo_documento = 'boleta'")
        _agregar_columna_si_no_existe(cursor, "movimientos_caja", "caja_sesion_id", "INTEGER")
        _agregar_columna_si_no_existe(cursor, "movimientos_caja", "categoria", "TEXT")
        _agregar_columna_si_no_existe(cursor, "movimientos_caja", "pago_documento_id", "INTEGER")

        _agregar_columna_si_no_existe(cursor, "compras", "tipo_operacion", "TEXT NOT NULL DEFAULT 'compra_inventario'")
        _agregar_columna_si_no_existe(cursor, "compras", "tipo_documento", "TEXT NOT NULL DEFAULT 'factura'")
        _agregar_columna_si_no_existe(cursor, "compras", "estado_pago", "TEXT NOT NULL DEFAULT 'pagado'")
        _agregar_columna_si_no_existe(cursor, "compras", "saldo_pendiente", "REAL NOT NULL DEFAULT 0")
        _agregar_columna_si_no_existe(cursor, "compras", "cuenta_contable_id", "INTEGER")

        # ============================================================
        # ÍNDICES
        # ============================================================

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_productos_nombre ON productos(nombre)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_productos_codigo_barras ON productos(codigo_barras)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_productos_codigo_pos ON productos(codigo_pos)")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ventas_fecha ON ventas(fecha)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ventas_usuario_id ON ventas(usuario_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ventas_caja_sesion_id ON ventas(caja_sesion_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ventas_metodo_pago ON ventas(metodo_pago)")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_detalle_ventas_venta_id ON detalle_ventas(venta_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_detalle_ventas_producto_id ON detalle_ventas(producto_id)")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_compras_fecha ON compras(fecha)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_detalle_compras_compra_id ON detalle_compras(compra_id)")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_movimientos_inv_producto_fecha ON movimientos_inventario(producto_id, fecha)")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cajas_sesiones_estado ON cajas_sesiones(estado)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cajas_sesiones_usuario_id ON cajas_sesiones(usuario_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cajas_sesiones_fecha_apertura ON cajas_sesiones(fecha_apertura)")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_movimientos_caja_fecha ON movimientos_caja(fecha)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_movimientos_caja_sesion_id ON movimientos_caja(caja_sesion_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_movimientos_caja_tipo ON movimientos_caja(tipo)")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_historial_fecha ON historial(fecha)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_permisos_modulo_usuario ON permisos_modulo(usuario_id)")

        _agregar_columna_si_no_existe(cursor, "usuarios", "pregunta_seguridad", "TEXT")
        _agregar_columna_si_no_existe(cursor, "usuarios", "respuesta_hash", "TEXT")
        _agregar_columna_si_no_existe(cursor, "productos", "tipo_item", "VARCHAR(50) NOT NULL DEFAULT 'producto'")

        conn.commit()
        insertar_datos_base(conn)


def _agregar_columna_si_no_existe(cursor, tabla: str, columna: str, definicion_sql: str) -> None:
    cursor.execute(f"PRAGMA table_info({tabla})")
    columnas_existentes = [fila[1] for fila in cursor.fetchall()]

    if columna not in columnas_existentes:
        cursor.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {definicion_sql}")