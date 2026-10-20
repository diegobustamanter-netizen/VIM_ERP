import sys

_factor: float = 1.0
_ultimo_monitor = None
_autoescala_after_id = None

BASE_WIDTH = 1920
BASE_HEIGHT = 1080


def preparar_dpi_awareness() -> None:
    """Activa DPI awareness en Windows antes de crear la ventana principal."""
    if sys.platform != "win32":
        return

    try:
        import ctypes

        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor DPI aware
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass  # No es Windows o no se pudo aplicar DPI awareness (no critico)


def _metricas_monitor_windows(root):
    import ctypes
    from ctypes import wintypes

    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", ctypes.c_long),
            ("top", ctypes.c_long),
            ("right", ctypes.c_long),
            ("bottom", ctypes.c_long),
        ]

    class MONITORINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", ctypes.c_ulong),
            ("rcMonitor", RECT),
            ("rcWork", RECT),
            ("dwFlags", ctypes.c_ulong),
        ]

    hwnd = root.winfo_id()
    monitor = ctypes.windll.user32.MonitorFromWindow(hwnd, 2)

    info = MONITORINFO()
    info.cbSize = ctypes.sizeof(MONITORINFO)
    ctypes.windll.user32.GetMonitorInfoW(
        wintypes.HMONITOR(monitor),
        ctypes.byref(info)
    )

    work_w = max(1, info.rcWork.right - info.rcWork.left)
    work_h = max(1, info.rcWork.bottom - info.rcWork.top)

    dpi_scale = 1.0
    try:
        dpi = ctypes.windll.user32.GetDpiForWindow(hwnd)
        dpi_scale = dpi / 96.0
    except Exception:
        try:
            dpi = ctypes.windll.user32.GetDpiForSystem()
            dpi_scale = dpi / 96.0
        except Exception:
            pass  # Fallback: usar dpi_scale = 1.0

    return {
        "x": info.rcWork.left,
        "y": info.rcWork.top,
        "width": work_w,
        "height": work_h,
        "dpi_scale": dpi_scale,
        "monitor": int(monitor),
    }


def obtener_metricas_monitor(root):
    """Devuelve area util y DPI aproximado del monitor donde esta la ventana."""
    try:
        if sys.platform == "win32":
            return _metricas_monitor_windows(root)
    except Exception:
        pass

    try:
        return {
            "x": 0,
            "y": 0,
            "width": max(1, root.winfo_screenwidth()),
            "height": max(1, root.winfo_screenheight()),
            "dpi_scale": 1.0,
            "monitor": "default",
        }
    except Exception:
        return {
            "x": 0,
            "y": 0,
            "width": BASE_WIDTH,
            "height": BASE_HEIGHT,
            "dpi_scale": 1.0,
            "monitor": "fallback",
        }


def _calcular_factor(root) -> float:
    """
    Calcula el factor de escala basado en la resolución y DPI.

    FÓRMULA CORREGIDA (v2):
    Antes: factor = resolution_ratio / dpi_scale   ← BUG
    Ahora: factor = resolution_ratio * dpi_scale    ← CORREGIDO

    Por qué el bug: dividir por dpi_scale invertía el efecto del DPI de Windows.
    En un monitor 4K a 200% DPI, resolution_ratio=2.0, dpi_scale=2.0,
    la fórmula vieja daba 1.0 (sin escala), cuando debería dar ~1.35× para
    aprovechar los píxeles extra. La nueva fórmula multiplica, dando 2.0→1.35
    (limitado por el clamp superior).
    """
    metricas = obtener_metricas_monitor(root)
    res_ratio = min(
        metricas["width"] / BASE_WIDTH,
        metricas["height"] / BASE_HEIGHT,
    )
    dpi_scale = metricas.get("dpi_scale") or 1.0

    # Multiplicar resolución × DPI: ambos aportan a cuán grande debe verse
    factor = res_ratio * dpi_scale
    return max(0.65, min(1.50, factor))


def inicializar_escala(root) -> None:
    """Detecta resolucion/DPI inicial y calcula el factor global."""
    global _factor
    try:
        _factor = _calcular_factor(root)
    except Exception:
        _factor = 1.0  # Fallback seguro: sin escala


def actualizar_escala(root, tolerancia: float = 0.04) -> bool:
    """Recalcula la escala. Retorna True si cambio lo suficiente."""
    global _factor, _ultimo_monitor

    try:
        metricas = obtener_metricas_monitor(root)
        nuevo_factor = _calcular_factor(root)
        monitor_actual = (
            metricas.get("monitor"),
            metricas.get("width"),
            metricas.get("height"),
            round(metricas.get("dpi_scale") or 1.0, 2),
        )

        cambio_factor = abs(nuevo_factor - _factor) >= tolerancia
        cambio_monitor = _ultimo_monitor is not None and monitor_actual != _ultimo_monitor

        _ultimo_monitor = monitor_actual
        if cambio_factor or cambio_monitor:
            _factor = nuevo_factor
            return True
    except Exception:
        pass  # Actualizacion de escala fallo silenciosamente (no critico)

    return False


def registrar_autoescala(root, on_change=None, delay_ms: int = 250) -> None:
    """Revisa cambios de monitor/DPI al mover o redimensionar la ventana."""

    def _programar(event=None):
        global _autoescala_after_id
        if event is not None and event.widget is not root:
            return

        if _autoescala_after_id:
            try:
                root.after_cancel(_autoescala_after_id)
            except Exception:
                pass  # after_cancel puede fallar si el timer ya expiro

        def _revisar():
            global _autoescala_after_id
            _autoescala_after_id = None
            if actualizar_escala(root) and callable(on_change):
                on_change()

        _autoescala_after_id = root.after(delay_ms, _revisar)

    actualizar_escala(root, tolerancia=0)
    root.bind("<Configure>", _programar, add="+")


def escalar(px: int) -> int:
    return max(1, int(round(px * _factor)))


def escalar_fuente(size: int, minimo: int = 8, maximo: int | None = None) -> int:
    """
    Escala un tamaño de fuente con clamping más suave que el de elementos.

    El factor de fuente usa un rango [0.75, 1.35] sobre _factor para que
    el texto no se vuelva demasiado grande/pequeño en extremos de escala.
    Antes era [0.85, 1.18]: demasiado estrecho frente al rango de los
    elementos [0.65, 1.50] — en pantallas chicas el texto (0.85) desbordaba
    cajas escaladas a 0.65, y en 4K los paneles (1.5) se veían vacíos con
    texto a 1.18. El rango ampliado mantiene texto y cajas proporcionados.
    """
    font_raw = max(0.75, min(1.35, _factor))
    valor = max(minimo, int(round(size * font_raw)))
    if maximo is not None:
        valor = min(maximo, valor)
    return valor


def es_pantalla_compacta(root, ancho_limite: int = 1280, alto_limite: int = 760) -> bool:
    metricas = obtener_metricas_monitor(root)
    return metricas["width"] <= ancho_limite or metricas["height"] <= alto_limite


def obtener_minimo_ventana(root) -> tuple[int, int]:
    metricas = obtener_metricas_monitor(root)
    ancho = min(1000, max(760, metricas["width"] - 120))
    alto = min(650, max(520, metricas["height"] - 120))
    return int(ancho), int(alto)


def get_factor() -> float:
    return _factor
