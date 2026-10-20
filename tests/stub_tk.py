"""
Permite importar las pantallas (Tk) en pruebas, incluso donde no hay
tkinter instalado (por ejemplo, un servidor sin entorno gráfico).

Si tkinter existe, se usa el real; las pruebas igual reemplazan los
diálogos (guardar como, mensajes) para que nunca se abra una ventana.
"""
import sys
import types


class _Cualquiera:
    """Objeto que acepta cualquier llamada o atributo y no hace nada."""

    def __init__(self, *a, **k):
        pass

    def __call__(self, *a, **k):
        return _Cualquiera()

    def __getattr__(self, nombre):
        return _Cualquiera()


class _ModuloFalso(types.ModuleType):
    def __getattr__(self, nombre):
        if nombre.startswith("__"):
            raise AttributeError(nombre)
        return type(nombre, (_Cualquiera,), {})


def asegurar_tk():
    try:
        import tkinter  # noqa: F401
        import tkinter.filedialog  # noqa: F401
        import tkinter.messagebox  # noqa: F401
        return
    except ImportError:
        pass
    for nombre in ("tkinter", "tkinter.ttk", "tkinter.messagebox", "tkinter.filedialog", "tkcalendar"):
        sys.modules[nombre] = _ModuloFalso(nombre)
    raiz = sys.modules["tkinter"]
    raiz.ttk = sys.modules["tkinter.ttk"]
    raiz.messagebox = sys.modules["tkinter.messagebox"]
    raiz.filedialog = sys.modules["tkinter.filedialog"]


def modulo_reportes():
    asegurar_tk()
    from modulos.ventas_reportes import ventas_main
    return ventas_main
