import tkinter as tk
from modulos.utils_globales import limpiar_formato_numerico


class ProductosUtilsMixin:

    def mover_siguiente_campo(self, siguiente_campo):
        siguiente_campo.focus_set()
        if hasattr(siguiente_campo, "select_range"):
            siguiente_campo.select_range(0, tk.END)

    def actualizar_campos_segun_tipo(self):
        tipo_venta = self.combo_tipo_venta.get()
        tipo_item_val = self.combo_tipo_item.get() if hasattr(self, 'combo_tipo_item') else "producto"

        if tipo_venta == "peso":
            self.entry_precio_venta.config(state="normal")
            self.entry_precio_venta.delete(0, tk.END)
            self.entry_precio_venta.config(state="disabled")
            self.entry_precio_kilo.config(state="normal")
        else:
            self.entry_precio_kilo.config(state="normal")
            self.entry_precio_kilo.delete(0, tk.END)
            self.entry_precio_kilo.config(state="disabled")
            self.entry_precio_venta.config(state="normal")

        if tipo_item_val == "servicio":
            self.entry_stock.config(state="normal")
            self.entry_stock.delete(0, tk.END)
            self.entry_stock.insert(0, "0")
            self.entry_stock.config(state="disabled")
            
            self.entry_stock_minimo.config(state="normal")
            self.entry_stock_minimo.delete(0, tk.END)
            self.entry_stock_minimo.insert(0, "0")
            self.entry_stock_minimo.config(state="disabled")
        else:
            self.entry_stock.config(state="normal")
            self.entry_stock_minimo.config(state="normal")

    def convertir_float(self, valor):
        valor = str(valor).strip()
        if not valor:
            return 0.0
        # Limpiar puntos de miles y manejar comas decimales
        valor = limpiar_formato_numerico(valor)
        return float(valor.replace(",", "."))

    def formatear_moneda(self, valor):
        """Formatea valor como moneda con miles (.) y decimales (,) si existen."""
        try:
            valor = float(valor or 0)
            s_valor = f"{round(valor, 2):,.2f}".rstrip('0').rstrip('.')
            return "$ " + s_valor.replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")
        except Exception:
            return f"$ {valor}"

    def formatear_numero(self, valor):
        valor = float(valor or 0)
        return int(valor) if valor.is_integer() else valor