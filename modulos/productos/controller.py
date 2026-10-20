import tkinter as tk

from config import (
    COLOR_PRIMARIO,
    COLOR_BLANCO,
    COLOR_GRIS,
    COLOR_PELIGRO,
    FUENTE_BOTON,
    FUENTE_MODULO
)

from database import obtener_producto_por_id
from modulos.utils_globales import formatear_para_edicion, crear_frame_scrollable
from ui_scale import escalar

from .utils import ProductosUtilsMixin
from .form import ProductosFormMixin
from .tabla import ProductosTablaMixin
from .acciones import ProductosAccionesMixin
from .historial import ProductosHistorialMixin


class ModuloProductos(
    ProductosUtilsMixin,
    ProductosFormMixin,
    ProductosTablaMixin,
    ProductosAccionesMixin,
    ProductosHistorialMixin
):
    """Módulo de gestión de productos."""

    def __init__(self, root, frame_contenido, volver_menu):
        self.root = root
        self.frame_contenido = frame_contenido
        self.volver_menu = volver_menu

        self.producto_id = None
        self.tree = None
        self.lbl_total = None

        self.entry_buscar = None
        self.entry_codigo_barras = None
        self.entry_codigo_pos = None
        self.entry_nombre = None
        self.entry_descripcion = None
        self.entry_precio_compra = None
        self.entry_precio_venta = None
        self.entry_precio_kilo = None
        self.entry_stock = None
        self.entry_stock_minimo = None
        self.entry_categoria = None
        self.entry_proveedor = None
        self.combo_tipo_venta = None

        self.construir_interfaz()

    def construir_interfaz(self):
        parent = self.frame_contenido

        header = tk.Frame(parent, bg=COLOR_PRIMARIO, height=escalar(70))
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="🏷️  PRODUCTOS",
            font=FUENTE_MODULO,
            fg=COLOR_BLANCO,
            bg=COLOR_PRIMARIO
        ).pack(side="left", padx=escalar(20), pady=escalar(18))

        tk.Button(
            header,
            text="← Volver al Menú",
            bg=COLOR_PELIGRO,
            fg=COLOR_BLANCO,
            relief="flat",
            font=FUENTE_BOTON,
            cursor="hand2",
            command=self.volver_menu
        ).pack(side="right", padx=escalar(20), pady=escalar(18))

        cuerpo = tk.Frame(parent, bg=COLOR_GRIS)
        cuerpo.pack(fill="both", expand=True, padx=escalar(15), pady=escalar(15))
        cuerpo.grid_rowconfigure(0, weight=1)
        cuerpo.grid_columnconfigure(0, weight=0, minsize=max(300, escalar(360)))
        cuerpo.grid_columnconfigure(1, weight=1)

        frame_izquierdo = tk.Frame(cuerpo, bg=COLOR_BLANCO, bd=1, relief="solid")
        frame_izquierdo.grid(row=0, column=0, sticky="ns", padx=(0, 10))

        frame_derecho = tk.Frame(cuerpo, bg=COLOR_BLANCO, bd=1, relief="solid")
        frame_derecho.grid(row=0, column=1, sticky="nsew")

        scroll_form, form_inner = crear_frame_scrollable(frame_izquierdo, bg=COLOR_BLANCO)
        scroll_form.pack(fill="both", expand=True)

        self.crear_formulario(form_inner)
        self.crear_panel_derecho(frame_derecho)

        self.configurar_eventos_tabla()
        self.configurar_enter_campos()
        self.cargar_productos()
        self.actualizar_campos_segun_tipo()

        if self.entry_codigo_barras:
            self.entry_codigo_barras.focus_set()

    def configurar_eventos_tabla(self):
        if self.tree:
            self.tree.bind("<<TreeviewSelect>>", self.cargar_producto_desde_tabla)
            self.tree.bind("<Double-1>", self.cargar_producto_desde_tabla)

    def cargar_producto_desde_tabla(self, event=None):
        if not self.tree:
            return

        seleccion = self.tree.selection()
        if not seleccion:
            return

        item_id = seleccion[0]
        valores = self.tree.item(item_id, "values")

        if not valores:
            return

        try:
            producto_id = int(valores[0])
        except (ValueError, TypeError, IndexError):
            return

        producto = obtener_producto_por_id(producto_id)
        if not producto:
            return

        ProductosFormMixin.limpiar_formulario(self, limpiar_id=False)
        self.producto_id = producto["id"]

        self.entry_codigo_barras.insert(0, producto.get("codigo_barras") or "")
        self.entry_codigo_pos.insert(0, producto.get("codigo_pos") or "")
        self.entry_nombre.insert(0, producto.get("nombre") or "")
        self.entry_descripcion.insert(0, producto.get("descripcion") or "")
        self.entry_precio_compra.insert(0, formatear_para_edicion(producto.get("precio_compra")))

        self.entry_precio_venta.config(state="normal")
        self.entry_precio_venta.insert(0, formatear_para_edicion(producto.get("precio_venta")))

        self.entry_precio_kilo.config(state="normal")
        self.entry_precio_kilo.insert(0, formatear_para_edicion(producto.get("precio_por_kilo")))

        self.entry_stock.insert(0, formatear_para_edicion(producto.get("stock")))
        self.entry_stock_minimo.insert(0, formatear_para_edicion(producto.get("stock_minimo")))

        if self.entry_categoria:
            self.entry_categoria.insert(0, producto.get("categoria_nombre") or "")

        if self.entry_proveedor:
            self.entry_proveedor.insert(0, producto.get("proveedor_nombre") or "")

        if self.combo_tipo_venta:
            self.combo_tipo_venta.set(producto.get("tipo_venta") or "unidad")

        if hasattr(self, 'combo_tipo_item') and self.combo_tipo_item:
            self.combo_tipo_item.set(producto.get("tipo_item") or "producto")

        self.actualizar_campos_segun_tipo()
        if hasattr(self, '_verificar_exclusividad_codigos'):
            self._verificar_exclusividad_codigos()


def abrir_modulo_productos(root, frame_contenido, volver_menu):
    return ModuloProductos(root, frame_contenido, volver_menu)
