from database.productos import (
    obtener_producto_por_codigo,
    buscar_productos_por_nombre,
    obtener_producto_por_id,
    listar_productos,
)
from .pos_utils import moneda, numero, obtener_codigo_visible


class POSBusquedaMixin:
    def enfocar_busqueda(self):
        self.entry_busqueda.focus_set()
        self.entry_busqueda.select_range(0, "end")

    def enfocar_pago(self):
        self.entry_pago_cliente.focus_set()
        self.entry_pago_cliente.select_range(0, "end")

    def enfocar_busqueda_y_break(self):
        self.enfocar_busqueda()
        return "break"

    def ir_desde_tabla_productos_a_resumen(self, event=None):
        self.entry_pago_cliente.focus_set()
        self.entry_pago_cliente.select_range(0, "end")
        return "break"

    def ir_desde_tabla_ticket_a_resumen(self, event=None):
        self.entry_pago_cliente.focus_set()
        self.entry_pago_cliente.select_range(0, "end")
        return "break"

    def ir_desde_tabla_ticket_a_zona_izquierda(self, event=None):
        self.entry_busqueda.focus_set()
        self.entry_busqueda.select_range(0, "end")
        return "break"

    def obtener_producto_seleccionado(self):
        seleccion = self.tree_productos.selection()
        if not seleccion:
            return None

        valores = self.tree_productos.item(seleccion[0], "values")
        if not valores:
            return None

        try:
            producto_id = int(valores[0])
        except (ValueError, TypeError, IndexError):
            return None

        return obtener_producto_por_id(producto_id)

    def limpiar_tabla_productos(self):
        for item in self.tree_productos.get_children():
            self.tree_productos.delete(item)

    def insertar_producto_en_tabla(self, producto):
        if not producto:
            return

        producto_id = producto.get("id")
        codigo = obtener_codigo_visible(producto)
        nombre = producto.get("nombre") or ""
        tipo = producto.get("tipo_venta") or "unidad"
        tipo_item = producto.get("tipo_item") or "producto"
        stock_str = "N/A" if tipo_item == "servicio" else numero(producto.get("stock") or 0)

        if tipo == "peso":
            precio = moneda(producto.get("precio_por_kilo") or 0)
        else:
            precio = moneda(producto.get("precio_venta") or 0)

        self.tree_productos.insert(
            "",
            "end",
            values=(producto_id, codigo, nombre, tipo, precio, stock_str)
        )

    def seleccionar_primer_resultado(self, mover_foco=False):
        hijos = self.tree_productos.get_children()
        if not hijos:
            return False

        self.tree_productos.selection_set(hijos[0])
        self.tree_productos.focus(hijos[0])
        self.tree_productos.see(hijos[0])

        if mover_foco:
            self.tree_productos.focus_set()

        self.al_seleccionar_producto()
        return True

    def producto_por_codigo_exacto(self, texto):
        """Producto que coincide exactamente por código de barras o PLU."""
        return obtener_producto_por_codigo(texto)

    def buscar(self, mover_foco=False):
        texto = self.entry_busqueda.get().strip()
        self.limpiar_tabla_productos()

        if not texto:
            self.mostrar_todos(mover_foco=mover_foco, limpiar_entry=False)
            return

        producto = self.producto_por_codigo_exacto(texto)
        productos = [producto] if producto else buscar_productos_por_nombre(texto)

        for prod in productos:
            self.insertar_producto_en_tabla(prod)

        if productos:
            self.seleccionar_primer_resultado(mover_foco=mover_foco)

    def mostrar_todos(self, mover_foco=False, limpiar_entry=True):
        if limpiar_entry:
            self.entry_busqueda.delete(0, "end")

        self.limpiar_tabla_productos()

        productos = listar_productos()
        for prod in productos:
            self.insertar_producto_en_tabla(prod)

        self.seleccionar_primer_resultado(mover_foco=mover_foco)

    def enter_en_busqueda(self, event=None):
        """Enter en el buscador.

        Si lo tipeado es un código exacto (lector de barras o PLU), el producto
        se agrega directo al ticket: antes había que apretar Enter dos veces,
        una para buscar y otra para agregar, en cada ítem escaneado.

        Los productos por peso quedan afuera: ahí el cajero tiene que ingresar
        los kilos antes de agregar.
        """
        texto = self.entry_busqueda.get().strip()
        producto = self.producto_por_codigo_exacto(texto)

        if producto and (producto.get("tipo_venta") or "unidad") != "peso":
            self.limpiar_tabla_productos()
            self.insertar_producto_en_tabla(producto)
            if self.seleccionar_primer_resultado():
                self.agregar_producto_seleccionado()
                return "break"

        self.buscar(mover_foco=True)
        return "break"

    def enter_en_tabla_productos(self, event=None):
        producto = self.obtener_producto_seleccionado()
        if not producto:
            return "break"

        self.agregar_producto_seleccionado()
        return "break"

    def al_seleccionar_producto(self, event=None):
        producto = self.obtener_producto_seleccionado()
        self.actualizar_modo_venta(producto)