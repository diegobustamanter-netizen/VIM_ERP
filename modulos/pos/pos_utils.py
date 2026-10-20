from modulos.utils_globales import limpiar_formato_numerico

COLOR_FOCO = "#cc0000"
COLOR_BORDE_NORMAL = "#ffffff"


def convertir_float(valor, default=0.0):
    if valor is None:
        return default
    if isinstance(valor, (int, float)):
        return float(valor)
    try:
        # Limpiar puntos de miles antes de convertir
        texto = str(valor).strip()
        texto = limpiar_formato_numerico(texto)
        if not texto:
            return default
        return float(texto)
    except Exception:
        return default


def moneda(valor):
    """Formatea valor como moneda con miles (.) y decimales (,) si existen."""
    try:
        valor = float(valor or 0)
        # Formatear con miles y 2 decimales, luego limpiar ceros innecesarios
        s_valor = f"{round(valor, 2):,.2f}".rstrip('0').rstrip('.')
        # Intercambiar separadores
        return "$ " + s_valor.replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")
    except Exception:
        return f"$ {valor}"


def numero(valor):
    valor = float(valor or 0)
    return int(valor) if valor.is_integer() else round(valor, 3)


def obtener_codigo_visible(producto):
    if not producto:
        return ""

    codigo_barras = producto.get("codigo_barras") if isinstance(producto, dict) else None
    codigo_pos = producto.get("codigo_pos") if isinstance(producto, dict) else None

    if codigo_barras:
        return codigo_barras

    if codigo_pos:
        return f"PLU {codigo_pos}"

    return ""