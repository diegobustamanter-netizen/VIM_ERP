from decimal import Decimal, ROUND_HALF_UP

from .connection import session_db
from vim_logger import get_logger

_log = get_logger("finanzas.utils")

# ============================================================
# UTILIDADES DE IMPUESTOS Y FINANZAS
# ============================================================

def get_config(clave, default=""):
    """Obtiene un valor de la tabla configuracion."""
    try:
        with session_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT valor FROM configuracion WHERE clave = ?", (clave,))
            row = cursor.fetchone()
            if row:
                return row[0]
            return default
    except Exception as e:
        _log.warning(f"Error obteniendo configuracion '{clave}': {e}")
        return default

def redondear_peso(valor) -> int:
    """Redondea a peso entero con la regla de siempre: ,5 sube.

    round() de Python redondea los ,5 al número PAR ("redondeo bancario"):
    un IVA de 28,5 quedaba en 28 en vez de 29. Se usa Decimal para que el
    ,5 siempre suba y para no arrastrar errores de punto flotante.
    """
    return int(Decimal(str(valor)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def calcular_impuesto(neto: float, iva_pct: float) -> float:
    """Calcula el impuesto sobre un monto neto, redondeado a peso entero."""
    return redondear_peso(Decimal(str(neto)) * Decimal(str(iva_pct)) / 100)


def calcular_total_con_iva(neto: float, iva_pct: float, incluye_iva: bool = False) -> tuple[float, float]:
    """Calcula (total, impuesto) en PESOS ENTEROS.

    El peso chileno no tiene decimales, y el SII valida que
    neto + impuesto = total de forma exacta. Por eso se redondea uno de los
    dos valores y el tercero se obtiene POR RESTA, nunca por fórmula: así la
    suma cuadra siempre, sin importar el monto.

    Antes se devolvían decimales (una venta de $1.000 daba neto 840,3361 e
    IVA 159,6639). Eso ensuciaba los reportes con centavos inexistentes y
    habría hecho que el SII rechazara cada boleta.

    Si incluye_iva=True, `neto` es en realidad el monto bruto.
    """
    if incluye_iva:
        # El bruto manda: se despeja el neto y el IVA sale por diferencia.
        total = redondear_peso(neto)
        neto_real = redondear_peso(Decimal(total) / (1 + Decimal(str(iva_pct)) / 100))
        impuesto = total - neto_real
        return float(total), float(impuesto)

    # El neto manda: se calcula el IVA y el total sale por suma exacta.
    base = redondear_peso(neto)
    impuesto = calcular_impuesto(base, iva_pct)
    total = base + impuesto
    return float(total), float(impuesto)

def aplicar_redondeo(total: float, redondeo_activo: bool = False) -> float:
    """Redondea el total a múltiplo de $10 si está activo (ej: Chile).

    Terminado en 1-4 baja, en 5-9 sube (1234 -> 1230, 1235 -> 1240).
    """
    if redondeo_activo:
        return float(redondear_peso(Decimal(str(total)) / 10) * 10)
    return total


def calcular_totales_venta(subtotal: float, config: dict | None = None,
                           metodo_pago: str = "efectivo") -> dict:
    """Neto, IVA y total a cobrar de una venta. FUENTE ÚNICA de estos montos.

    La usan la pantalla del POS (lo que ve el cajero) y crear_venta (lo que se
    guarda). Antes cada uno calculaba por su lado: con "los precios ya
    incluyen IVA" desactivado, el POS mostraba $1.000 y el sistema cobraba
    $1.190, así que el pago justo se rechazaba y TODA venta con tarjeta fallaba.

    - subtotal: suma de las líneas, tal como están cargados los precios.
    - Si los precios incluyen IVA, el total es el subtotal y el IVA se despeja.
      Si no, el IVA se suma encima.
    - El redondeo a $10 se aplica SOLO a pagos en efectivo (con tarjeta o
      transferencia se cobra el monto exacto) y no cambia el IVA.
    """
    if config is None:
        config = obtener_config_finanzas()
    iva_pct = float(config.get("iva_porcentaje") or 0)
    incluido = bool(config.get("iva_incluido", True))

    total_exacto, impuesto = calcular_total_con_iva(subtotal, iva_pct, incluye_iva=incluido)
    total = total_exacto
    if metodo_pago == "efectivo":
        total = aplicar_redondeo(total_exacto, bool(config.get("redondeo_automatico")))

    return {
        "neto": total_exacto - impuesto,
        "impuesto": impuesto,
        "total": total,
        "ajuste_redondeo": total - total_exacto,
        "iva_porcentaje": iva_pct,
        "iva_incluido": incluido,
    }


def obtener_config_finanzas() -> dict:
    """Obtiene la configuración financiera actual."""
    claves = ["iva_porcentaje", "iva_incluido", "redondeo_automatico", "moneda", "regimen_tributario"]
    config = {}
    for clave in claves:
        val = (get_config(clave, "") or "").strip()
        if clave == "iva_porcentaje":
            try:
                config[clave] = float(val.replace(",", ".")) if val else 19.0
            except ValueError:
                _log.warning(f"iva_porcentaje inválido en configuración: {val!r}; se usa 19")
                config[clave] = 19.0
        elif clave == "iva_incluido":
            # Sin configurar = precios con IVA incluido, como en la instalación
            # nueva y como se exhiben los precios al público en Chile.
            config[clave] = val in ("1", "True", "true") if val else True
        elif clave == "redondeo_automatico":
            config[clave] = val in ("1", "True", "true")
        else:
            config[clave] = val or ""
    return config