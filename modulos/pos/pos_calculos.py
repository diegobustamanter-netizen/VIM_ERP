"""Cálculos del POS, sin dependencias de interfaz.

Separado de pos_ticket.py a propósito: acá no se importa tkinter, así que
estas decisiones se pueden probar de forma automática sin abrir una ventana.
pos_ticket se limita a pintar el resultado en los widgets.
"""

# Colores del recuadro de vuelto según el estado del pago
VERDE_TEXTO = "#2e7d32"
VERDE_FONDO = "#e8f5e9"
ROJO_TEXTO = "#c62828"
ROJO_FONDO = "#fdecea"


def estado_del_pago(total, pago):
    """Decide qué mostrar en el recuadro de vuelto.

    Devuelve un dict con:
      titulo : "VUELTO" o "FALTA"
      monto  : cuánto sobra, o cuánto falta (siempre positivo)
      falta  : True si el pago no cubre el total
      color / fondo : colores del recuadro

    El caso importante es `falta`: antes el vuelto negativo se forzaba a 0 y
    el cajero veía "$ 0" sin distinguir un pago justo de uno insuficiente.

    Con el campo de pago vacío (0) no se considera faltante: el cliente
    todavía no entregó nada, no hay nada que reclamar.
    """
    try:
        total = float(total or 0)
        pago = float(pago or 0)
    except (TypeError, ValueError):
        total, pago = 0.0, 0.0

    diferencia = pago - total
    falta = diferencia < 0 and pago > 0

    if falta:
        return {
            "titulo": "FALTA",
            "monto": abs(diferencia),
            "falta": True,
            "color": ROJO_TEXTO,
            "fondo": ROJO_FONDO,
        }

    return {
        "titulo": "VUELTO",
        "monto": max(diferencia, 0),
        "falta": False,
        "color": VERDE_TEXTO,
        "fondo": VERDE_FONDO,
    }
