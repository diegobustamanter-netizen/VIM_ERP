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

def calcular_impuesto(neto: float, iva_pct: float) -> float:
    """Calcula el impuesto sobre un monto neto, redondeado a peso entero."""
    return round(neto * (iva_pct / 100))


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
        total = round(neto)
        neto_real = round(total / (1 + iva_pct / 100))
        impuesto = total - neto_real
        return float(total), float(impuesto)

    # El neto manda: se calcula el IVA y el total sale por suma exacta.
    base = round(neto)
    impuesto = round(base * (iva_pct / 100))
    total = base + impuesto
    return float(total), float(impuesto)

def aplicar_redondeo(total: float, redondeo_activo: bool = False) -> float:
    """Aplica redondeo automático si está activo (ej: Chile)."""
    if redondeo_activo:
        # Redondeo a múltiplo de 10 (ej: 1234 -> 1230 o 1240)
        return round(total / 10) * 10
    return total

def obtener_config_finanzas() -> dict:
    """Obtiene la configuración financiera actual."""
    claves = ["iva_porcentaje", "iva_incluido", "redondeo_automatico", "moneda", "regimen_tributario"]
    config = {}
    for clave in claves:
        val = get_config(clave, "")
        if clave == "iva_porcentaje":
            config[clave] = float(val) if val else 19.0
        elif clave in ["iva_incluido", "redondeo_automatico"]:
            config[clave] = val in ("1", "True", "true")
        else:
            config[clave] = val or ""
    return config