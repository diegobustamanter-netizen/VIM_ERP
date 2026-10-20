# ============================================================
# IMPRESIÓN TÉRMICA ESC/POS (58mm / 80mm) — Windows
# ============================================================
# Envía comandos ESC/POS crudos (RAW) a la cola de impresión de
# Windows usando winspool vía ctypes. No requiere dependencias
# externas (compatible con el .exe de PyInstaller sin cambios).
#
# Funciona con la gran mayoría de impresoras térmicas de boleta
# (58mm y 80mm) instaladas como impresora en Windows, ya que casi
# todas hablan el protocolo ESC/POS de Epson.
#
# NOTA LEGAL (Chile): el ticket impreso es un COMPROBANTE INTERNO
# de venta. NO constituye boleta electrónica válida ante el SII.
# La emisión de boletas electrónicas requiere un sistema autorizado
# por el SII (el emisor gratuito del SII o un proveedor certificado).
# ============================================================

import sys
import ctypes
from ctypes import wintypes

from vim_logger import get_logger

_log = get_logger("impresion.termica")

# ── Comandos ESC/POS ─────────────────────────────────────────
ESC = b"\x1b"
GS = b"\x1d"

CMD_INIT = ESC + b"@"                  # Reset de impresora
CMD_CODEPAGE_PC850 = ESC + b"t\x02"    # Tabla de caracteres PC850 (latino)
CMD_ALIGN_LEFT = ESC + b"a\x00"
CMD_ALIGN_CENTER = ESC + b"a\x01"
CMD_BOLD_ON = ESC + b"E\x01"
CMD_BOLD_OFF = ESC + b"E\x00"
CMD_DOBLE_ON = GS + b"!\x11"           # Doble ancho + doble alto
CMD_DOBLE_OFF = GS + b"!\x00"
CMD_FEED_Y_CORTE = GS + b"V\x42\x03"   # Alimentar y corte parcial (GS V 66 n)

# Caracteres por línea en fuente estándar (Font A, 12x24)
ANCHO_58MM = 32
ANCHO_80MM = 48


# ============================================================
# CAPA WINDOWS (winspool vía ctypes)
# ============================================================

class _DOC_INFO_1W(ctypes.Structure):
    _fields_ = [
        ("pDocName", wintypes.LPWSTR),
        ("pOutputFile", wintypes.LPWSTR),
        ("pDatatype", wintypes.LPWSTR),
    ]


class _PRINTER_INFO_4W(ctypes.Structure):
    _fields_ = [
        ("pPrinterName", wintypes.LPWSTR),
        ("pServerName", wintypes.LPWSTR),
        ("Attributes", wintypes.DWORD),
    ]


def _winspool():
    if sys.platform != "win32":
        raise RuntimeError("La impresión térmica solo está disponible en Windows.")
    return ctypes.WinDLL("winspool.drv", use_last_error=True)


def listar_impresoras():
    """Devuelve la lista de nombres de impresoras instaladas en Windows."""
    try:
        spool = _winspool()
    except Exception:
        get_logger("impresion").exception("No se pudo acceder al spooler para listar impresoras")
        return []

    PRINTER_ENUM_LOCAL = 0x00000002
    PRINTER_ENUM_CONNECTIONS = 0x00000004
    flags = PRINTER_ENUM_LOCAL | PRINTER_ENUM_CONNECTIONS

    needed = wintypes.DWORD(0)
    devueltas = wintypes.DWORD(0)

    # Primera llamada: obtener tamaño del buffer
    spool.EnumPrintersW(flags, None, 4, None, 0,
                        ctypes.byref(needed), ctypes.byref(devueltas))
    if needed.value == 0:
        return []

    buffer = (ctypes.c_byte * needed.value)()
    ok = spool.EnumPrintersW(flags, None, 4, buffer, needed.value,
                             ctypes.byref(needed), ctypes.byref(devueltas))
    if not ok:
        _log.warning(f"EnumPrintersW fallo (error {ctypes.get_last_error()})")
        return []

    impresoras = []
    info_arr = ctypes.cast(buffer, ctypes.POINTER(_PRINTER_INFO_4W * devueltas.value)).contents
    for info in info_arr:
        if info.pPrinterName:
            impresoras.append(info.pPrinterName)
    return impresoras


def obtener_impresora_predeterminada():
    """Nombre de la impresora predeterminada de Windows, o ''."""
    try:
        spool = _winspool()
    except Exception:
        get_logger("impresion").exception("No se pudo obtener la impresora predeterminada")
        return ""
    tam = wintypes.DWORD(0)
    spool.GetDefaultPrinterW(None, ctypes.byref(tam))
    if tam.value == 0:
        return ""
    buffer = ctypes.create_unicode_buffer(tam.value)
    if spool.GetDefaultPrinterW(buffer, ctypes.byref(tam)):
        return buffer.value
    return ""


def _imprimir_raw(nombre_impresora: str, datos: bytes):
    """Envía bytes crudos (RAW) a la cola de una impresora de Windows.

    Lanza RuntimeError con mensaje claro si algo falla, para que la UI
    pueda mostrarlo al usuario (que es quien tiene la impresora).
    """
    spool = _winspool()

    handle = wintypes.HANDLE()
    if not spool.OpenPrinterW(nombre_impresora, ctypes.byref(handle), None):
        raise RuntimeError(
            f"No se pudo abrir la impresora '{nombre_impresora}' "
            f"(error {ctypes.get_last_error()}). Verifique que esté instalada y en línea."
        )

    try:
        doc = _DOC_INFO_1W()
        doc.pDocName = "VIM ERP - Ticket de venta"
        doc.pOutputFile = None
        doc.pDatatype = "RAW"

        if not spool.StartDocPrinterW(handle, 1, ctypes.byref(doc)):
            raise RuntimeError(
                f"La impresora '{nombre_impresora}' rechazó el documento "
                f"(error {ctypes.get_last_error()})."
            )
        try:
            spool.StartPagePrinter(handle)
            escritos = wintypes.DWORD(0)
            ok = spool.WritePrinter(handle, datos, len(datos), ctypes.byref(escritos))
            spool.EndPagePrinter(handle)
            if not ok or escritos.value != len(datos):
                raise RuntimeError(
                    f"Error enviando datos a '{nombre_impresora}': se escribieron "
                    f"{escritos.value} de {len(datos)} bytes."
                )
        finally:
            spool.EndDocPrinter(handle)
    finally:
        spool.ClosePrinter(handle)

    _log.info(f"Ticket enviado a '{nombre_impresora}' ({len(datos)} bytes)")


# ============================================================
# GENERACIÓN DEL TICKET (texto ESC/POS)
# ============================================================

def _texto(s: str) -> bytes:
    """Codifica texto a PC850 (acentos y ñ). Caracteres raros → '?'."""
    return str(s).encode("cp850", errors="replace")


def _fila(izq: str, der: str, ancho: int) -> str:
    """Una línea con texto a la izquierda y a la derecha, rellena al ancho."""
    espacio = ancho - len(izq) - len(der)
    if espacio < 1:
        izq = izq[: max(0, ancho - len(der) - 1)]
        espacio = ancho - len(izq) - len(der)
    return izq + " " * max(1, espacio) + der


def _envolver(texto: str, ancho: int):
    """Corta un texto en líneas de máximo `ancho` caracteres, por palabras."""
    palabras = str(texto).split()
    lineas, actual = [], ""
    for p in palabras:
        candidata = (actual + " " + p).strip()
        if len(candidata) <= ancho:
            actual = candidata
        else:
            if actual:
                lineas.append(actual)
            actual = p[:ancho]
    if actual:
        lineas.append(actual)
    return lineas or [""]


def _moneda(valor) -> str:
    """$1.234 estilo chileno (sin decimales)."""
    try:
        return "$" + f"{round(float(valor)):,}".replace(",", ".")
    except Exception:
        return f"${valor}"


def generar_ticket_escpos(datos: dict, config: dict) -> bytes:
    """Construye los bytes ESC/POS de un ticket de venta.

    datos: {folio, fecha, cajero, metodo_pago, lineas:[{nombre, cantidad_txt, subtotal}],
            subtotal, impuesto, total, pago, vuelto}
    config: {ticket_tamano, ticket_desglose_iva, ticket_mensaje_pie,
             nombre_negocio, rut_empresa, giro_empresa, direccion_empresa,
             telefono_empresa, iva_porcentaje}
    """
    ancho = ANCHO_58MM if config.get("ticket_tamano", "58mm") == "58mm" else ANCHO_80MM
    sep = "-" * ancho

    out = bytearray()
    out += CMD_INIT
    out += CMD_CODEPAGE_PC850

    # ── Encabezado ───────────────────────────────────────────
    out += CMD_ALIGN_CENTER
    nombre = (config.get("nombre_negocio") or "VIM ERP").strip()
    out += CMD_BOLD_ON
    for ln in _envolver(nombre.upper(), ancho):
        out += _texto(ln) + b"\n"
    out += CMD_BOLD_OFF

    for clave, prefijo in (("rut_empresa", "RUT: "), ("giro_empresa", ""),
                           ("direccion_empresa", ""), ("telefono_empresa", "Tel: ")):
        val = (config.get(clave) or "").strip()
        if val:
            for ln in _envolver(prefijo + val, ancho):
                out += _texto(ln) + b"\n"

    out += _texto(sep) + b"\n"

    # ── Datos de la venta ────────────────────────────────────
    out += CMD_ALIGN_LEFT
    out += _texto(_fila(f"Folio: {datos.get('folio', '')}", "", ancho)) + b"\n"
    out += _texto(_fila(f"Fecha: {datos.get('fecha', '')}", "", ancho)) + b"\n"
    if datos.get("cajero"):
        out += _texto(f"Cajero: {datos['cajero']}") + b"\n"
    out += _texto(f"Pago: {str(datos.get('metodo_pago', '')).capitalize()}") + b"\n"
    out += _texto(sep) + b"\n"

    # ── Ítems ────────────────────────────────────────────────
    for linea in datos.get("lineas", []):
        nombre_prod = str(linea.get("nombre", ""))
        cant_txt = str(linea.get("cantidad_txt", ""))
        subtotal_txt = _moneda(linea.get("subtotal", 0))

        # Nombre (envuelto) y luego cantidad + subtotal alineado a la derecha
        for ln in _envolver(nombre_prod, ancho):
            out += _texto(ln) + b"\n"
        out += _texto(_fila("  " + cant_txt, subtotal_txt, ancho)) + b"\n"

    out += _texto(sep) + b"\n"

    # ── Desglose IVA (opcional) ──────────────────────────────
    if str(config.get("ticket_desglose_iva", "1")) in ("1", "True", "true"):
        try:
            impuesto = float(datos.get("impuesto") or 0)
            total_f = float(datos.get("total") or 0)
            neto = total_f - impuesto
            iva_pct = float(config.get("iva_porcentaje") or 19)
            if impuesto > 0:
                out += _texto(_fila("NETO:", _moneda(neto), ancho)) + b"\n"
                out += _texto(_fila(f"IVA ({iva_pct:g}%):", _moneda(impuesto), ancho)) + b"\n"
        except Exception as e:
            # El desglose es informativo: nunca debe impedir imprimir el
            # ticket. Pero si falla, el cliente recibe un comprobante sin el
            # detalle del impuesto y hay que poder enterarse.
            from vim_logger import get_logger
            get_logger("impresion.ticket").warning(
                f"No se pudo calcular el desglose de IVA del ticket: {e}"
            )

    # ── Total (letra grande) ─────────────────────────────────
    out += CMD_BOLD_ON + CMD_DOBLE_ON
    # En doble ancho caben ancho//2 caracteres por línea
    out += _texto(_fila("TOTAL", _moneda(datos.get("total", 0)), ancho // 2)) + b"\n"
    out += CMD_DOBLE_OFF + CMD_BOLD_OFF

    if str(datos.get("metodo_pago")) == "efectivo":
        out += _texto(_fila("Efectivo:", _moneda(datos.get("pago", 0)), ancho)) + b"\n"
        out += _texto(_fila("Vuelto:", _moneda(datos.get("vuelto", 0)), ancho)) + b"\n"

    out += _texto(sep) + b"\n"

    # ── Pie ──────────────────────────────────────────────────
    out += CMD_ALIGN_CENTER
    pie = (config.get("ticket_mensaje_pie") or "").strip()
    if pie:
        for ln in _envolver(pie, ancho):
            out += _texto(ln) + b"\n"
    for ln in _envolver("Comprobante interno de venta", ancho):
        out += _texto(ln) + b"\n"
    for ln in _envolver("No valido como boleta (SII)", ancho):
        out += _texto(ln) + b"\n"

    out += b"\n"
    out += CMD_FEED_Y_CORTE
    return bytes(out)


# ============================================================
# API DE ALTO NIVEL (usada por POS y Configuración)
# ============================================================

def _cargar_config_impresion() -> dict:
    from modulos.configuracion.utils import get_configs
    return get_configs([
        "impresora_termica", "impresion_automatica",
        "ticket_tamano", "ticket_desglose_iva", "ticket_mensaje_pie",
        "ticket_copias", "nombre_negocio", "rut_empresa", "giro_empresa",
        "direccion_empresa", "telefono_empresa", "iva_porcentaje",
    ])


def impresora_configurada() -> str:
    """Nombre de la impresora configurada, o '' si no hay."""
    try:
        return (_cargar_config_impresion().get("impresora_termica") or "").strip()
    except Exception:
        get_logger("impresion").exception("No se pudo leer la impresora configurada")
        return ""


def imprimir_ticket_venta(datos: dict, copias: int | None = None):
    """Imprime un ticket de venta en la impresora configurada.

    Lanza RuntimeError con mensaje entendible si no hay impresora
    configurada o si la impresión falla. El llamador decide si eso
    bloquea o no el flujo (en el POS NO debe bloquear la venta).
    """
    config = _cargar_config_impresion()
    impresora = (config.get("impresora_termica") or "").strip()
    if not impresora:
        raise RuntimeError(
            "No hay impresora configurada. Vaya a Configuración → Empresa "
            "y seleccione su impresora térmica."
        )

    if copias is None:
        try:
            copias = max(1, min(5, int(config.get("ticket_copias") or 1)))
        except (ValueError, TypeError):
            copias = 1

    payload = generar_ticket_escpos(datos, config)
    for _ in range(copias):
        _imprimir_raw(impresora, payload)


# ============================================================
# COMPROBANTE EN PDF (sin impresora)
# ============================================================
# Sirve para entregar el comprobante por correo/WhatsApp y para probar
# el formato sin tener una impresora térmica. Se arma a mano (PDF 1.4 con
# la fuente Courier de serie) para no sumar dependencias al .exe.

_COMANDOS_ESCPOS = (CMD_INIT, CMD_CODEPAGE_PC850, CMD_ALIGN_LEFT, CMD_ALIGN_CENTER,
                    CMD_BOLD_ON, CMD_BOLD_OFF, CMD_DOBLE_ON, CMD_DOBLE_OFF,
                    CMD_FEED_Y_CORTE)


def _lineas_del_ticket(datos: dict, config: dict):
    """El mismo ticket que se imprime, como líneas de texto plano.

    Se parte de los bytes ESC/POS para que el PDF nunca se aparte de lo que
    sale en papel: se respeta la alineación y se quitan los demás comandos.
    """
    ancho = ANCHO_58MM if config.get("ticket_tamano", "58mm") == "58mm" else ANCHO_80MM
    crudo = generar_ticket_escpos(datos, config)
    crudo = crudo.replace(CMD_ALIGN_CENTER, b"\x01").replace(CMD_ALIGN_LEFT, b"\x02")
    for cmd in _COMANDOS_ESCPOS:
        crudo = crudo.replace(cmd, b"")

    lineas, centrado, actual = [], False, ""
    for car in crudo.decode("cp850", errors="replace"):
        if car == "\x01":
            centrado = True
        elif car == "\x02":
            centrado = False
        elif car == "\n":
            if centrado:
                actual = actual.center(ancho).rstrip()
            elif actual.startswith("TOTAL"):
                # En papel va en letra doble: en el PDF se ocupa todo el ancho
                actual = _fila("TOTAL", actual[len("TOTAL"):].strip(), ancho)
            lineas.append(actual.rstrip())
            actual = ""
        else:
            actual += car
    while lineas and not lineas[-1].strip():
        lineas.pop()
    return lineas, ancho


def _escapar_pdf(texto: str) -> bytes:
    t = texto.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return t.encode("cp1252", errors="replace")


def generar_ticket_pdf(datos: dict, config: dict | None = None) -> bytes:
    """Bytes de un PDF de una página con el comprobante, del ancho del papel."""
    config = dict(config if config is not None else _cargar_config_impresion())
    lineas, ancho = _lineas_del_ticket(datos, config)

    fuente, interlinea, margen = 9, 11, 14
    ancho_pt = int(ancho * fuente * 0.6 + 2 * margen)
    alto_pt = int(len(lineas) * interlinea + 2 * margen)

    contenido = bytearray(b"BT /F1 %d Tf %d TL %d %d Td\n" % (fuente, interlinea, margen, alto_pt - margen - fuente))
    for ln in lineas:
        contenido += b"(" + _escapar_pdf(ln) + b") Tj T*\n"
    contenido += b"ET\n"

    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>" % (ancho_pt, alto_pt),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>",
        b"<< /Length %d >>\nstream\n" % len(contenido) + bytes(contenido) + b"endstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    posiciones = []
    for i, obj in enumerate(objetos, start=1):
        posiciones.append(len(pdf))
        pdf += b"%d 0 obj\n" % i + obj + b"\nendobj\n"
    inicio_xref = len(pdf)
    pdf += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objetos) + 1)
    for pos in posiciones:
        pdf += b"%010d 00000 n \n" % pos
    pdf += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objetos) + 1, inicio_xref)
    return bytes(pdf)


def guardar_ticket_pdf(datos: dict, ruta: str, config: dict | None = None) -> str:
    """Guarda el comprobante como PDF en `ruta` y la devuelve."""
    with open(ruta, "wb") as f:
        f.write(generar_ticket_pdf(datos, config))
    _log.info(f"Comprobante guardado como PDF: {ruta}")
    return ruta


def datos_de_ejemplo():
    """Venta ficticia para la página de prueba y la vista previa."""
    from database.utils import ahora
    return {
        "folio": "PRUEBA-001",
        "fecha": ahora("%d/%m/%Y %H:%M"),
        "cajero": "Prueba",
        "metodo_pago": "efectivo",
        "lineas": [
            {"nombre": "Producto de prueba", "cantidad_txt": "x1", "subtotal": 1000},
            {"nombre": "Producto con nombre muy largo para probar el ajuste de linea",
             "cantidad_txt": "x2", "subtotal": 5990},
        ],
        "impuesto": 1116,
        "total": 6990,
        "pago": 10000,
        "vuelto": 3010,
    }


def imprimir_pagina_prueba(nombre_impresora: str, tamano: str = "58mm"):
    """Imprime una página de prueba para verificar la conexión."""
    datos = datos_de_ejemplo()
    config = _cargar_config_impresion()
    config["ticket_tamano"] = tamano
    payload = generar_ticket_escpos(datos, config)
    _imprimir_raw(nombre_impresora, payload)
