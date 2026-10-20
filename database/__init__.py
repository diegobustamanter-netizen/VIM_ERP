from .connection import conectar_db, session_db
from .utils import ahora
from .historial import registrar_movimiento, registrar_historial, obtener_historial
from .schema import inicializar_db

# ============================================================
# PRODUCTOS
# ============================================================
from .productos import (
    crear_producto,
    actualizar_producto,
    eliminar_producto,
    obtener_producto_por_id,
    obtener_producto_por_codigo_barras,
    obtener_producto_por_codigo_pos,
    buscar_productos_por_nombre,
    obtener_productos,
    listar_productos,
    obtener_categoria_id_por_nombre,
    obtener_proveedor_id_por_nombre,
)

# ============================================================
# VENTAS
# ============================================================
from .ventas import (
    generar_folio_venta,
    confirmar_venta,
    crear_venta,
    obtener_venta_por_id,
)

# ============================================================
# CAJA
# ============================================================
from .caja import (
    abrir_caja,
    obtener_caja_abierta,
    obtener_caja_abierta_por_usuario,
    registrar_movimiento_caja,
    obtener_movimientos_caja,
    obtener_resumen_caja,
    cerrar_caja,
)