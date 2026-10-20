import sqlite3
import sqlite3
import secrets
import string
from .utils import ahora


def _generar_password_temporal(longitud: int = 6) -> str:
    """Genera una contraseña temporal aleatoria con letras y dígitos."""
    caracteres = string.ascii_letters + string.digits
    return ''.join(secrets.choice(caracteres) for _ in range(longitud))


def insertar_datos_base(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()

    categorias_base = [
        ("Abarrotes", "Productos de despensa"),
        ("Bebidas", "Bebidas y líquidos"),
        ("Lácteos", "Leche, quesos y derivados"),
        ("Congelados", "Productos congelados"),
        ("Limpieza", "Artículos de limpieza"),
        ("Confites", "Dulces y snacks"),
    ]

    for nombre, descripcion in categorias_base:
        cursor.execute(
            """
            INSERT OR IGNORE INTO categorias (nombre, descripcion, activa, fecha_creacion)
            VALUES (?, ?, 1, ?)
            """,
            (nombre, descripcion, ahora()),
        )

    # ============================================================
    # PLAN DE CUENTAS INICIAL (ERP)
    # ============================================================
    plan_cuentas_base = [
        ("1.1", "Mercaderías", "egreso", 1),
        ("2.1", "Luz", "egreso", 0),
        ("2.2", "Agua", "egreso", 0),
        ("2.3", "Arriendo", "egreso", 0),
        ("2.4", "Internet / Teléfono", "egreso", 0),
        ("2.5", "Sueldos y Salarios", "egreso", 0),
        ("2.6", "Papelería / Oficina", "egreso", 0),
        ("2.7", "Mantenimiento / Reparaciones", "egreso", 0),
        ("2.8", "Transporte / Fletes", "egreso", 0),
        ("2.9", "Publicidad / Marketing", "egreso", 0),
        ("3.1", "Honorarios Profesionales", "egreso", 0),
        ("4.1", "Impuestos", "egreso", 0),
        ("5.1", "Otros Gastos Operacionales", "egreso", 0),
        ("6.1", "Maquinaria y Equipo", "activo", 0),
        ("6.2", "Instalaciones / Mobiliario", "activo", 0),
    ]

    for codigo, nombre, tipo, es_inv in plan_cuentas_base:
        cursor.execute(
            """
            INSERT OR IGNORE INTO plan_cuentas (codigo, nombre, tipo, es_inventariable, activo)
            VALUES (?, ?, ?, ?, 1)
            """,
            (codigo, nombre, tipo, es_inv),
        )

    # ============================================================
    # EMPLEADOS DEMO
    # ============================================================
    cursor.execute("SELECT COUNT(*) FROM empleados")
    if cursor.fetchone()[0] == 0:
        empleados_demo = [
            ("12.345.678-9", "Juan Pérez", "Cajero", 450000, ahora()),
            ("18.765.432-1", "María López", "Administradora", 850000, ahora()),
        ]
        for e in empleados_demo:
            cursor.execute(
                """
                INSERT INTO empleados (rut, nombre, cargo, sueldo_base, fecha_ingreso, activo)
                VALUES (?, ?, ?, ?, ?, 1)
                """,
                e
            )

    cursor.execute(
        """
        INSERT OR IGNORE INTO configuracion (clave, valor, descripcion)
        VALUES
            ('moneda', 'CLP', 'Moneda principal del sistema'),
            ('nombre_negocio', 'VIM ERP', 'Nombre comercial del negocio'),
            ('iva_porcentaje', '19', 'Porcentaje referencial de impuesto'),
            ('iva_incluido', '1', 'Si los precios incluyen IVA (1=si, 0=no)'),
            ('redondeo_automatico', '0', 'Aplicar redondeo automático (1=si, 0=no)'),
            ('regimen_tributario', 'Pro Pyme (Art 14 D)', 'Régimen tributario aplicable'),
            ('tipo_negocio', '', 'Tipo de negocio: productos o servicios (vacío = preguntar al iniciar)')
        """
    )

    MODULOS_DISPONIBLES = [
        "pos", "inventario", "productos", "reportes",
        "compras", "caja", "usuarios", "configuracion", "backup"
    ]

    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        from modulos.seguridad.auth import hash_password
        password_temporal = "1234"
        cursor.execute(
            """
            INSERT INTO usuarios (username, password_hash, nombre, rol, activo, fecha_creacion)
            VALUES (?, ?, ?, ?, 1, ?)
            """,
            ("admin", hash_password(password_temporal), "Administrador", "administrador", ahora()),
        )
        # Guardar para onboarding
        cursor.execute(
            """
            INSERT OR REPLACE INTO configuracion (clave, valor, descripcion)
            VALUES ('admin_temp_password', ?, 'Contraseña temporal del admin (borrar tras primer login)')
            """,
            (password_temporal,),
        )

    # Asegurar que todos los usuarios tengan sus filas de permisos
    cursor.execute("SELECT id, rol FROM usuarios")
    todos_usuarios = cursor.fetchall()
    for uid, rol in todos_usuarios:
        for modulo in MODULOS_DISPONIBLES:
            # Admin siempre tiene todos los permisos; otros usuarios tienen permisos según rol
            if rol == "administrador":
                permitido = 1
            elif rol == "supervisor":
                permitido = 1 if modulo in ("pos", "inventario", "productos", "reportes", "compras", "caja") else 0
            else:  # cajero
                permitido = 1 if modulo in ("pos", "caja") else 0
            cursor.execute(
                "INSERT OR IGNORE INTO permisos_modulo (usuario_id, modulo, permitido) VALUES (?, ?, ?)",
                (uid, modulo, permitido)
            )

    cursor.execute(
        """
        INSERT OR IGNORE INTO proveedores (
            nombre, rut, telefono, email, direccion, contacto, activo, fecha_creacion
        )
        VALUES (?, ?, ?, ?, ?, ?, 1, ?)
        """,
        (
            "Proveedor Demo",
            "76.123.456-7",
            "+56 9 1234 5678",
            "demo@proveedor.cl",
            "Santiago",
            "Vendedor Demo",
            ahora(),
        ),
    )

    cursor.execute("SELECT id, nombre FROM categorias")
    categorias = {nombre: cid for cid, nombre in cursor.fetchall()}

    cursor.execute("SELECT id FROM proveedores WHERE nombre = ?", ("Proveedor Demo",))
    fila_proveedor = cursor.fetchone()
    proveedor_demo_id = fila_proveedor[0] if fila_proveedor else None

    cursor.execute("SELECT COUNT(*) FROM productos")
    cantidad_productos = cursor.fetchone()[0]

    if cantidad_productos == 0:
        productos_demo = [
            ("7801000000011", "1001", "Coca-Cola 1.5L", "Bebida gaseosa 1.5 litros", categorias.get("Bebidas"), proveedor_demo_id, 1200, 1790, 0, 25, 5, "unidad", "unidad"),
            ("7801000000028", "1002", "Pan de Molde Blanco", "Pan de molde tradicional", categorias.get("Abarrotes"), proveedor_demo_id, 1100, 1690, 0, 18, 4, "unidad", "unidad"),
            ("7801000000035", "1003", "Leche Entera 1L", "Leche entera caja 1 litro", categorias.get("Lácteos"), proveedor_demo_id, 800, 1190, 0, 30, 6, "unidad", "unidad"),
            ("7801000000042", "1004", "Detergente 1Kg", "Detergente en polvo", categorias.get("Limpieza"), proveedor_demo_id, 2500, 3490, 0, 12, 3, "unidad", "unidad"),
            ("7801000000059", "1005", "Chocolate Barra 100g", "Chocolate de leche", categorias.get("Confites"), proveedor_demo_id, 600, 990, 0, 40, 8, "unidad", "unidad"),
            ("7801000000066", "1006", "Helado Cassata", "Helado familiar cassata", categorias.get("Congelados"), proveedor_demo_id, 3200, 4590, 0, 10, 2, "unidad", "unidad"),
            (None, "2001", "Manzana Granel", "Venta por kilo", categorias.get("Abarrotes"), proveedor_demo_id, 1200, 0, 1990, 35, 5, "kg", "peso"),
            (None, "2002", "Plátano Granel", "Venta por kilo", categorias.get("Abarrotes"), proveedor_demo_id, 1000, 0, 1690, 28, 5, "kg", "peso"),
            (None, "2003", "Tomate Granel", "Venta por kilo", categorias.get("Abarrotes"), proveedor_demo_id, 900, 0, 1490, 22, 4, "kg", "peso"),
            (None, "2004", "Queso Laminado", "Producto de venta por kilo", categorias.get("Lácteos"), proveedor_demo_id, 4800, 0, 7990, 15, 3, "kg", "peso"),
        ]

        for p in productos_demo:
            cursor.execute(
                """
                INSERT INTO productos (
                    codigo_barras, codigo_pos, nombre, descripcion,
                    categoria_id, proveedor_id, precio_compra, precio_venta,
                    precio_por_kilo, stock, stock_minimo, unidad_medida,
                    tipo_venta, permite_descuento, activo, fecha_creacion
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1, ?)
                """,
                (*p, ahora()),
            )

    conn.commit()