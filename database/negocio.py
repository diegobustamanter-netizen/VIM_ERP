"""Modo de negocio: el sistema opera como negocio de PRODUCTOS o de SERVICIOS.

Un local vende cosas (almacén, minimarket) o presta servicios (peluquería,
taller). Mezclar ambos es raro, así que en vez de marcar ítem por ítem se
define una sola vez para todo el sistema y cada ítem nuevo hereda ese tipo.

La ventaja es que todo el circuito de venta ya sabe tratar tipo_item =
'servicio' (no descuenta stock, no genera movimiento de inventario, no lo
devuelve al anular). Este módulo solo decide qué valor se estampa y qué
partes de la interfaz y de los reportes tienen sentido mostrar.
"""

from typing import Any, Dict, List

from .connection import session_db

MODO_PRODUCTOS = "productos"
MODO_SERVICIOS = "servicios"

CLAVE_CONFIG = "tipo_negocio"

# Caché en memoria: obtener_modo_negocio() se llama al construir pantallas y
# al armar reportes. Sin caché sería una conexión SQLite nueva cada vez.
# Se invalida al guardar el modo (establecer_modo_negocio).
_modo_cache = None


def invalidar_cache() -> None:
    """Olvida el modo cacheado. Llamar tras cambiar la configuración."""
    global _modo_cache
    _modo_cache = None


def _leer_modo_crudo() -> str:
    """Lee la clave tal cual está en la BD ('' si nunca se configuró)."""
    try:
        with session_db() as conn:
            fila = conn.execute(
                "SELECT valor FROM configuracion WHERE clave = ?", (CLAVE_CONFIG,)
            ).fetchone()
            return (fila[0] or "").strip().lower() if fila else ""
    except Exception:
        # Si la tabla todavía no existe (primer arranque, antes del seed)
        # se asume productos: es el comportamiento histórico del sistema.
        return ""


def modo_configurado() -> bool:
    """True si el dueño ya eligió el tipo de negocio alguna vez."""
    return _leer_modo_crudo() in (MODO_PRODUCTOS, MODO_SERVICIOS)


def obtener_modo_negocio() -> str:
    """Modo actual. Si nunca se configuró, devuelve 'productos'."""
    global _modo_cache
    if _modo_cache is None:
        valor = _leer_modo_crudo()
        _modo_cache = valor if valor in (MODO_PRODUCTOS, MODO_SERVICIOS) else MODO_PRODUCTOS
    return _modo_cache


def es_negocio_de_servicios() -> bool:
    return obtener_modo_negocio() == MODO_SERVICIOS


def tipo_item_por_defecto() -> str:
    """Valor que debe llevar productos.tipo_item para los ítems nuevos."""
    return "servicio" if es_negocio_de_servicios() else "producto"


# ============================================================
# ETIQUETAS PARA LA INTERFAZ
# ============================================================

def etiqueta_item(plural: bool = False, capitalizar: bool = False) -> str:
    """'producto'/'servicio' según el modo, para armar textos de la interfaz."""
    if es_negocio_de_servicios():
        texto = "servicios" if plural else "servicio"
    else:
        texto = "productos" if plural else "producto"
    return texto.capitalize() if capitalizar else texto


def etiqueta_costo_unitario() -> str:
    """Cómo llamar al campo precio_compra en el formulario."""
    return "Costo Directo:" if es_negocio_de_servicios() else "Precio Compra:"


def etiqueta_costo_ventas() -> str:
    """Cómo llamar al costo de ventas en los reportes."""
    if es_negocio_de_servicios():
        return "Costo directo de servicios"
    return "Costo de Ventas (COGS)"


def maneja_inventario() -> bool:
    """True si tiene sentido hablar de stock, proveedores y valorización."""
    return not es_negocio_de_servicios()


# ============================================================
# QUÉ APLICA AL REGISTRAR COMPRAS Y GASTOS
# ============================================================

def tipos_de_operacion_disponibles() -> List[str]:
    """Tipos de operación que se pueden registrar en Compras.

    Un negocio de servicios no repone inventario, así que ofrecer
    'compra_inventario' solo lleva a clasificar mal un gasto, y esa mala
    clasificación termina distorsionando el Estado de Resultados.
    """
    tipos = ["gasto_operativo", "sueldos", "activo_fijo"]
    if maneja_inventario():
        tipos.insert(0, "compra_inventario")
    return tipos


def cuentas_aplicables(cuentas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filtra el plan de cuentas según el tipo de negocio.

    Sin inventario, las cuentas inventariables (Mercaderías) no aplican.
    """
    if maneja_inventario():
        return list(cuentas)
    return [c for c in cuentas if not c.get("es_inventariable")]


# ============================================================
# CAMBIO DE MODO
# ============================================================

def contar_items_a_convertir(modo_destino: str) -> int:
    """Cuántos ítems activos quedarían con un tipo distinto al modo destino."""
    tipo_destino = "servicio" if modo_destino == MODO_SERVICIOS else "producto"
    try:
        with session_db() as conn:
            fila = conn.execute(
                """
                SELECT COUNT(*) FROM productos
                WHERE activo = 1 AND COALESCE(tipo_item, 'producto') != ?
                """,
                (tipo_destino,)
            ).fetchone()
            return fila[0] if fila else 0
    except Exception:
        return 0


def convertir_items(modo_destino: str) -> int:
    """Pasa todos los ítems al tipo que corresponde al modo destino.

    Al convertir a servicios se anula el stock, porque un servicio no se
    inventaría. NO se tocan las ventas históricas: los reportes de períodos
    anteriores siguen mostrando lo que realmente pasó.

    Devuelve la cantidad de ítems convertidos.
    """
    tipo_destino = "servicio" if modo_destino == MODO_SERVICIOS else "producto"

    with session_db() as conn:
        cursor = conn.cursor()
        if tipo_destino == "servicio":
            cursor.execute(
                """
                UPDATE productos
                SET tipo_item = 'servicio', stock = 0, stock_minimo = 0
                WHERE COALESCE(tipo_item, 'producto') != 'servicio'
                """
            )
        else:
            cursor.execute(
                """
                UPDATE productos
                SET tipo_item = 'producto'
                WHERE COALESCE(tipo_item, 'producto') != 'producto'
                """
            )
        convertidos = cursor.rowcount
        conn.commit()

    return convertidos


def establecer_modo_negocio(modo: str, convertir: bool = False) -> int:
    """Guarda el modo de negocio. Si convertir=True, adapta los ítems.

    Devuelve la cantidad de ítems convertidos (0 si convertir=False).
    """
    if modo not in (MODO_PRODUCTOS, MODO_SERVICIOS):
        raise ValueError(f"Modo de negocio inválido: {modo}")

    convertidos = convertir_items(modo) if convertir else 0

    with session_db() as conn:
        conn.execute(
            """
            INSERT INTO configuracion (clave, valor, descripcion)
            VALUES (?, ?, 'Tipo de negocio: productos o servicios')
            ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor
            """,
            (CLAVE_CONFIG, modo)
        )
        conn.commit()

    invalidar_cache()
    return convertidos
