import tkinter as tk
from tkinter import ttk, messagebox

from config import (
    COLOR_PRIMARIO,
    COLOR_SECUNDARIO,
    COLOR_BLANCO,
    COLOR_PELIGRO,
    COLOR_PELIGRO_HOVER,
    FUENTE_BOTON
)

from modulos.utils_globales import formatear_con_miles
from ui_scale import escalar_fuente
from database.negocio import es_negocio_de_servicios, tipo_item_por_defecto


class ProductosFormMixin:
    def crear_formulario(self, parent):
        parent.grid_columnconfigure(1, weight=1)

        tk.Label(
            parent,
            text="Gestión de Productos",
            font=("Segoe UI", escalar_fuente(16), "bold"),
            bg=COLOR_BLANCO,
            fg=COLOR_PRIMARIO
        ).grid(row=0, column=0, columnspan=2, padx=15, pady=15, sticky="w")

        self.entry_codigo_barras = self.crear_campo(parent, "Código de barras:", 1)
        self.entry_codigo_pos = self.crear_campo(parent, "Código POS / PLU:", 2)
        
        self.entry_codigo_barras.bind("<KeyRelease>", self._verificar_exclusividad_codigos, add="+")
        self.entry_codigo_pos.bind("<KeyRelease>", self._verificar_exclusividad_codigos, add="+")

        self.entry_nombre = self.crear_campo(parent, "Nombre:", 3)
        self.entry_descripcion = self.crear_campo(parent, "Descripción:", 4)

        self._lbl_tipo_item = tk.Label(
            parent,
            text="Tipo de ítem:",
            bg=COLOR_BLANCO,
            fg="black",
            font=("Segoe UI", escalar_fuente(10), "bold")
        )
        self._lbl_tipo_item.grid(row=5, column=0, sticky="w", padx=15, pady=6)

        self.combo_tipo_item = ttk.Combobox(
            parent,
            values=["producto", "servicio", "combo"],
            state="readonly",
            font=("Segoe UI", escalar_fuente(10)),
            width=26
        )
        self.combo_tipo_item.grid(row=5, column=1, padx=15, pady=6, sticky="ew")
        self.combo_tipo_item.set(tipo_item_por_defecto())
        self.combo_tipo_item.bind("<<ComboboxSelected>>", lambda e: self.actualizar_campos_segun_tipo())

        # En un negocio de servicios todos los ítems son servicios: el selector
        # sobra y solo invita a crear datos inconsistentes. Se oculta pero el
        # widget sigue vivo, porque el resto del formulario lo consulta.
        if es_negocio_de_servicios():
            self._lbl_tipo_item.grid_remove()
            self.combo_tipo_item.grid_remove()

        self._lbl_tipo_venta = tk.Label(
            parent,
            text="Tipo de venta:",
            bg=COLOR_BLANCO,
            fg="black",
            font=("Segoe UI", escalar_fuente(10), "bold")
        )
        self._lbl_tipo_venta.grid(row=6, column=0, sticky="w", padx=15, pady=6)

        self.combo_tipo_venta = ttk.Combobox(
            parent,
            values=["unidad", "peso"],
            state="readonly",
            font=("Segoe UI", escalar_fuente(10)),
            width=26
        )
        self.combo_tipo_venta.grid(row=6, column=1, padx=15, pady=6, sticky="ew")
        self.combo_tipo_venta.set("unidad")
        self.combo_tipo_venta.bind("<<ComboboxSelected>>", lambda e: self.actualizar_campos_segun_tipo())
        self.combo_tipo_venta.bind("<Return>", lambda e: self.mover_siguiente_campo(self.entry_precio_compra))

        _servicios = es_negocio_de_servicios()

        # En servicios el "precio de compra" es en realidad el costo directo
        # del servicio (insumos + comisión). Es opcional: si queda en 0, los
        # reportes omiten la línea de costo y la de margen.
        self.entry_precio_compra = self.crear_campo(
            parent, "Costo directo:" if _servicios else "Precio compra:", 7
        )
        self.entry_precio_venta = self.crear_campo(
            parent, "Precio del servicio:" if _servicios else "Precio venta:", 8
        )
        self.entry_precio_kilo = self.crear_campo(parent, "Precio por kilo:", 9)

        self.entry_stock = self.crear_campo(parent, "Stock:", 11)
        self.entry_stock_minimo = self.crear_campo(parent, "Stock mínimo:", 12)
        self.entry_categoria = self.crear_campo(parent, "Categoría:", 13)
        self.entry_proveedor = self.crear_campo(parent, "Proveedor:", 14)

        # Un servicio no se inventaría ni se le compra a un proveedor: esos
        # campos se ocultan. Los widgets siguen existiendo (el guardado los
        # lee) y utils.actualizar_campos_segun_tipo ya los deja en 0.
        if _servicios:
            for campo in (self.entry_stock, self.entry_stock_minimo,
                          self.entry_precio_kilo, self.entry_proveedor):
                campo.grid_remove()
                campo._lbl.grid_remove()

            # Un servicio no se vende por peso. Si el selector quedara visible
            # y alguien eligiera "peso", el precio pasaría al campo por kilo
            # que está oculto y no habría forma de cargarlo.
            self.combo_tipo_venta.set("unidad")
            self._lbl_tipo_venta.grid_remove()
            self.combo_tipo_venta.grid_remove()

        frame_botones = tk.Frame(parent, bg=COLOR_BLANCO)
        frame_botones.grid(row=15, column=0, columnspan=2, pady=5, padx=15, sticky="ew")

        tk.Button(
            frame_botones,
            text="Guardar",
            width=14,
            bg=COLOR_SECUNDARIO,
            fg=COLOR_BLANCO,
            relief="flat",
            font=FUENTE_BOTON,
            cursor="hand2",
            command=self.guardar_producto
        ).grid(row=0, column=0, padx=5, pady=5)

        tk.Button(
            frame_botones,
            text="Actualizar",
            width=14,
            bg=COLOR_PRIMARIO,
            fg=COLOR_BLANCO,
            relief="flat",
            font=FUENTE_BOTON,
            cursor="hand2",
            command=self.actualizar_producto
        ).grid(row=0, column=1, padx=5, pady=5)

        tk.Button(
            frame_botones,
            text="Nuevo / Limpiar",
            width=14,
            bg="#6c757d",
            fg=COLOR_BLANCO,
            relief="flat",
            font=FUENTE_BOTON,
            cursor="hand2",
            command=self.limpiar_formulario
        ).grid(row=1, column=0, padx=5, pady=5)

        boton_eliminar = tk.Button(
            frame_botones,
            text="Eliminar",
            width=14,
            bg=COLOR_PELIGRO,
            fg=COLOR_BLANCO,
            relief="flat",
            font=FUENTE_BOTON,
            cursor="hand2",
            command=self.eliminar_producto
        )
        boton_eliminar.grid(row=1, column=1, padx=5, pady=5)
        boton_eliminar.bind("<Enter>", lambda e: boton_eliminar.config(bg=COLOR_PELIGRO_HOVER))
        boton_eliminar.bind("<Leave>", lambda e: boton_eliminar.config(bg=COLOR_PELIGRO))

        tk.Button(
            parent,
            text="Historial",
            width=31,
            bg=COLOR_PRIMARIO,
            fg=COLOR_BLANCO,
            relief="flat",
            font=FUENTE_BOTON,
            cursor="hand2",
            command=self.abrir_historial
        ).grid(row=16, column=0, columnspan=2, padx=15, pady=(0, 12), sticky="ew")

    def crear_campo(self, parent, texto, fila):
        lbl = tk.Label(
            parent,
            text=texto,
            bg=COLOR_BLANCO,
            fg="black",
            font=("Segoe UI", escalar_fuente(10), "bold")
        )
        lbl.grid(row=fila, column=0, sticky="w", padx=15, pady=6)

        entry = tk.Entry(parent, font=("Segoe UI", escalar_fuente(10)), width=28)
        entry.grid(row=fila, column=1, padx=15, pady=6, sticky="ew")

        # Aplicar formateador de miles si es un campo de precio o stock.
        # "Costo" está incluido porque en negocios de servicios el campo de
        # precio de compra se muestra como "Costo directo".
        nombres_numericos = ["Precio", "Stock", "Costo"]
        if any(n in texto for n in nombres_numericos):
            entry.bind("<KeyRelease>", formatear_con_miles, add="+")

        # Referencia a la etiqueta: permite ocultar la fila completa según el
        # tipo de negocio (ej. stock en un negocio de servicios).
        entry._lbl = lbl
        return entry

    def _verificar_exclusividad_codigos(self, event=None):
        if not hasattr(self, 'entry_codigo_barras') or not hasattr(self, 'entry_codigo_pos'):
            return
            
        barras = self.entry_codigo_barras.get().strip()
        pos = self.entry_codigo_pos.get().strip()

        if barras:
            self.entry_codigo_pos.config(state="disabled")
        else:
            self.entry_codigo_pos.config(state="normal")

        if pos:
            self.entry_codigo_barras.config(state="disabled")
        else:
            self.entry_codigo_barras.config(state="normal")

    def configurar_enter_campos(self):
        campos = [
            self.entry_codigo_barras,
            self.entry_codigo_pos,
            self.entry_nombre,
            self.entry_descripcion,
            self.combo_tipo_item,
            self.combo_tipo_venta,
            self.entry_precio_compra,
            self.entry_precio_venta,
            self.entry_precio_kilo,
            self.entry_stock,
            self.entry_stock_minimo,
            self.entry_categoria,
            self.entry_proveedor
        ]

        for i, campo in enumerate(campos[:-1]):
            siguiente = campos[i + 1]
            campo.bind("<Return>", lambda e, s=siguiente: self.mover_siguiente_campo(s))

        self.entry_proveedor.bind("<Return>", lambda e: self.guardar_producto())

    def obtener_datos_formulario(self):
        codigo_barras = self.entry_codigo_barras.get().strip()
        codigo_pos = self.entry_codigo_pos.get().strip()
        nombre = self.entry_nombre.get().strip()
        descripcion = self.entry_descripcion.get().strip()
        tipo_item = self.combo_tipo_item.get().strip() or "producto"
        tipo_venta = self.combo_tipo_venta.get().strip() or "unidad"
        precio_compra = self.entry_precio_compra.get().strip()
        precio_venta = self.entry_precio_venta.get().strip()
        precio_kilo = self.entry_precio_kilo.get().strip()
        
        if tipo_item == "servicio":
            stock = "0"
            stock_minimo = "0"
        else:
            stock = self.entry_stock.get().strip()
            stock_minimo = self.entry_stock_minimo.get().strip()
            
        categoria = self.entry_categoria.get().strip()
        proveedor = self.entry_proveedor.get().strip()

        if not nombre:
            messagebox.showwarning("Validación", "El nombre del producto es obligatorio.")
            self.entry_nombre.focus_set()
            return None

        if not codigo_barras and not codigo_pos:
            messagebox.showwarning("Validación", "Debes ingresar código de barras o código POS.")
            self.entry_codigo_barras.focus_set()
            return None

        try:
            precio_compra = self.convertir_float(precio_compra)
            precio_venta = self.convertir_float(precio_venta)
            precio_kilo = self.convertir_float(precio_kilo)
            stock = self.convertir_float(stock)
            stock_minimo = self.convertir_float(stock_minimo)
        except ValueError:
            messagebox.showerror("Error", "Revisa los campos numéricos.")
            return None

        if precio_compra < 0 or precio_venta < 0 or precio_kilo < 0:
            messagebox.showerror("Error", "Los precios no pueden ser negativos.")
            return None

        if stock < 0 or stock_minimo < 0:
            messagebox.showerror("Error", "El stock no puede ser negativo.")
            return None

        if tipo_venta == "unidad" and precio_venta <= 0:
            messagebox.showerror("Error", "Para productos por unidad debes ingresar un precio de venta válido.")
            self.entry_precio_venta.focus_set()
            return None

        if tipo_venta == "peso" and precio_kilo <= 0:
            messagebox.showerror("Error", "Para productos por peso debes ingresar un precio por kilo válido.")
            self.entry_precio_kilo.focus_set()
            return None

        return (
            codigo_barras,
            codigo_pos,
            nombre,
            descripcion,
            precio_compra,
            precio_venta,
            precio_kilo,
            stock,
            stock_minimo,
            categoria,
            proveedor,
            tipo_venta,
            tipo_item
        )

    def limpiar_formulario(self, limpiar_id=True):
        entradas = [
            self.entry_codigo_barras,
            self.entry_codigo_pos,
            self.entry_nombre,
            self.entry_descripcion,
            self.entry_precio_compra,
            self.entry_precio_venta,
            self.entry_precio_kilo,
            self.entry_stock,
            self.entry_stock_minimo,
            self.entry_categoria,
            self.entry_proveedor
        ]

        for entry in entradas:
            entry.config(state="normal")
            entry.delete(0, tk.END)

        self.combo_tipo_item.set("producto")
        self.combo_tipo_venta.set("unidad")
        self.actualizar_campos_segun_tipo()
        self._verificar_exclusividad_codigos()

        if limpiar_id:
            self.producto_id = None

        self.entry_codigo_barras.focus_set()
