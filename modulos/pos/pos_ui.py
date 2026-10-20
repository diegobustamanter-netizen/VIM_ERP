import tkinter as tk
from tkinter import ttk

from ui_scale import escalar, escalar_fuente, es_pantalla_compacta

from config import COLOR_PRIMARIO, COLOR_SECUNDARIO, COLOR_BLANCO, COLOR_GRIS, COLOR_PELIGRO, FUENTE_BOTON

from modulos.utils_globales import formatear_con_miles
from database.negocio import es_negocio_de_servicios


class POSInterfazMixin:
    """Construcción de la interfaz del Punto de Venta.

    Métodos de ModuloPOS (ver pos_main.py). Antes se asignaban a mano
    a la clase, uno por uno, al final de aquel archivo.
    """

    def construir_interfaz(self):
        for widget in self.frame_contenido.winfo_children():
            widget.destroy()

        parent = self.frame_contenido

        # ============================================================
        # HEADER
        # ============================================================
        header = tk.Frame(parent, bg=COLOR_PRIMARIO, height=escalar(56))
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="🛒  PUNTO DE VENTA (POS)",
            font=("Segoe UI", escalar_fuente(16), "bold"),
            fg=COLOR_BLANCO,
            bg=COLOR_PRIMARIO
        ).pack(side="left", padx=escalar(20), pady=escalar(12))

        if not es_pantalla_compacta(self.root):
            atajos_frame = tk.Frame(header, bg=COLOR_PRIMARIO)
            atajos_frame.pack(side="left", padx=escalar(30))
            for texto in ["F2 Cobrar", "F4 Buscar", "F5 Todos", "Esc Salir"]:
                tk.Label(atajos_frame, text=texto, font=("Segoe UI", escalar_fuente(8)), fg="#8ab4f8",
                         bg=COLOR_PRIMARIO).pack(side="left", padx=escalar(8))

        self.btn_cerrar = tk.Button(
            header,
            text="← Volver al Menú",
            bg=COLOR_PELIGRO,
            fg=COLOR_BLANCO,
            relief="flat",
            font=FUENTE_BOTON,
            cursor="hand2",
            command=self.volver_menu,
            takefocus=1
        )
        self.btn_cerrar.pack(side="right", padx=escalar(20), pady=escalar(12))

        # ============================================================
        # CUERPO
        # ============================================================
        cuerpo = tk.Frame(parent, bg=COLOR_GRIS)
        cuerpo.pack(fill="both", expand=True, padx=max(6, escalar(10)), pady=max(6, escalar(10)))
        cuerpo.grid_rowconfigure(0, weight=1)
        cuerpo.grid_columnconfigure(0, weight=5, minsize=escalar(250))
        cuerpo.grid_columnconfigure(1, weight=4, minsize=escalar(220))
        cuerpo.grid_columnconfigure(2, weight=3, minsize=escalar(200))

        izquierda = tk.Frame(cuerpo, bg=COLOR_BLANCO, bd=1, relief="solid")
        izquierda.grid(row=0, column=0, sticky="nsew", padx=(0, escalar(5)))

        centro = tk.Frame(cuerpo, bg=COLOR_BLANCO, bd=1, relief="solid")
        centro.grid(row=0, column=1, sticky="nsew", padx=escalar(5))

        derecha = tk.Frame(cuerpo, bg=COLOR_BLANCO, bd=1, relief="solid")
        derecha.grid(row=0, column=2, sticky="nsew", padx=(escalar(5), 0))

        self.crear_panel_busqueda(izquierda)
        self.crear_panel_ticket(centro)
        self.crear_panel_resumen(derecha)

        self.aplicar_resalte_boton(self.btn_cerrar, COLOR_PELIGRO)

        if self.entry_busqueda:
            self.entry_busqueda.focus_set()

        self.root.after(50, self.mostrar_todos)


    # ============================================================
    # PANEL DE BÚSQUEDA Y PRODUCTOS
    # ============================================================

    def crear_panel_busqueda(self, parent):
        frame = tk.Frame(parent, bg=COLOR_BLANCO)
        frame.pack(fill="x", padx=escalar(12), pady=(escalar(10), escalar(6)))

        tk.Label(
            frame,
            text=("Buscar servicio:" if es_negocio_de_servicios()
                  else "Escanear código o buscar producto:"),
            bg=COLOR_BLANCO,
            fg="#555",
            font=("Segoe UI", escalar_fuente(9), "bold")
        ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, escalar(5)))

        self.entry_busqueda = tk.Entry(
            frame,
            font=("Segoe UI", escalar_fuente(13)),
            width=28,
            takefocus=1
        )
        self.entry_busqueda.grid(row=1, column=0, padx=(0, escalar(6)), pady=escalar(3), sticky="ew")
        self.entry_busqueda.bind("<KeyRelease>", lambda e: _buscar_en_vivo(self))

        self.btn_buscar = tk.Button(
            frame,
            text="🔍 Buscar",
            bg=COLOR_SECUNDARIO,
            fg=COLOR_BLANCO,
            relief="flat",
            font=("Segoe UI", escalar_fuente(9), "bold"),
            cursor="hand2",
            command=self.buscar,
            takefocus=1
        )
        self.btn_buscar.grid(row=1, column=1, padx=escalar(3), pady=escalar(3), sticky="ew")

        tk.Label(
            frame, text="Cant.:", bg=COLOR_BLANCO,
            font=("Segoe UI", escalar_fuente(9), "bold")
        ).grid(row=2, column=0, padx=(0, escalar(3)), pady=(escalar(5), escalar(3)), sticky="w")

        self.entry_cantidad = tk.Entry(
            frame, font=("Segoe UI", escalar_fuente(11)), width=6, takefocus=1, justify="center"
        )
        self.entry_cantidad.grid(row=2, column=1, padx=escalar(3), pady=(escalar(5), escalar(3)), sticky="ew")
        self.entry_cantidad.insert(0, "1")
        self.entry_cantidad.bind("<KeyRelease>", formatear_con_miles, add="+")

        tk.Label(
            frame, text="Peso kg:", bg=COLOR_BLANCO,
            font=("Segoe UI", escalar_fuente(9), "bold")
        ).grid(row=2, column=2, padx=(escalar(10), escalar(3)), pady=(escalar(5), escalar(3)), sticky="w")

        self.entry_peso = tk.Entry(
            frame, font=("Segoe UI", escalar_fuente(11)), width=6, takefocus=1, justify="center"
        )
        self.entry_peso.grid(row=2, column=3, padx=escalar(3), pady=(escalar(5), escalar(3)), sticky="ew")
        self.entry_peso.insert(0, "1")

        self.btn_agregar = tk.Button(
            frame,
            text="➕ Agregar",
            bg="#28a745",
            fg=COLOR_BLANCO,
            relief="flat",
            font=("Segoe UI", escalar_fuente(9), "bold"),
            cursor="hand2",
            command=self.agregar_producto_seleccionado,
            takefocus=1
        )
        self.btn_agregar.grid(row=1, column=2, columnspan=2, padx=(escalar(8), 0), pady=escalar(3), sticky="ew")

        self.lbl_modo = tk.Label(
            frame,
            text="Modo: sin producto seleccionado",
            bg=COLOR_BLANCO,
            fg=COLOR_PRIMARIO,
            font=("Segoe UI", escalar_fuente(8), "bold")
        )
        self.lbl_modo.grid(row=3, column=0, columnspan=4, sticky="w", pady=(escalar(4), 0))

        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=0)
        frame.grid_columnconfigure(2, weight=0)
        frame.grid_columnconfigure(3, weight=0)

        style = ttk.Style()
        style.configure(
            "Productos.Treeview",
            rowheight=escalar(28),
            font=("Segoe UI", escalar_fuente(10))
        )
        style.configure(
            "Productos.Treeview.Heading",
            font=("Segoe UI", escalar_fuente(10), "bold"),
            background="#e2e8f0",
            foreground="#333333",
            relief="flat"
        )

        tabla_frame = tk.Frame(parent, bg=COLOR_BLANCO)
        tabla_frame.pack(fill="both", expand=True, padx=escalar(12), pady=(0, escalar(6)))

        columnas = ("id", "codigo", "nombre", "tipo", "precio", "stock")

        self.tree_productos = ttk.Treeview(
            tabla_frame,
            columns=columnas,
            show="headings",
            style="Productos.Treeview"
        )

        self.tree_productos.heading("id", text="ID")
        self.tree_productos.heading("codigo", text="Código")
        self.tree_productos.heading("nombre", text="Nombre")
        self.tree_productos.heading("tipo", text="Tipo")
        self.tree_productos.heading("precio", text="Precio")
        self.tree_productos.heading("stock", text="Stock")

        self.tree_productos.column("id", width=escalar(40), anchor="center")
        self.tree_productos.column("codigo", width=escalar(110), anchor="center")
        self.tree_productos.column("nombre", width=escalar(200), anchor="w")
        self.tree_productos.column("tipo", width=escalar(60), anchor="center")
        self.tree_productos.column("precio", width=escalar(100), anchor="e")
        self.tree_productos.column("stock", width=escalar(70), anchor="center")

        # En un negocio de servicios la columna Stock siempre diría "N/A":
        # se esconde y el espacio se lo queda el nombre.
        if es_negocio_de_servicios():
            self.tree_productos["displaycolumns"] = ("id", "codigo", "nombre", "tipo", "precio")
            self.tree_productos.column("nombre", width=escalar(260), anchor="w")

        scrollbar = ttk.Scrollbar(tabla_frame, orient="vertical", command=self.tree_productos.yview)
        self.tree_productos.configure(yscrollcommand=scrollbar.set)

        self.tree_productos.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree_productos.bind("<<TreeviewSelect>>", self.al_seleccionar_producto)
        self.tree_productos.bind("<Double-1>", lambda e: self.agregar_producto_seleccionado())
        self.tree_productos.bind("<Return>", lambda e: self.agregar_producto_seleccionado())
        self.tree_productos.bind("<Right>", self.ir_desde_tabla_productos_a_resumen)
        self.tree_productos.bind("<Left>", lambda e: self.enfocar_busqueda_y_break())
        self.tree_productos.bind("<Escape>", lambda e: self.enfocar_busqueda_y_break())

        botones = tk.Frame(parent, bg=COLOR_BLANCO)
        botones.pack(fill="x", padx=escalar(12), pady=(0, escalar(8)))

        self.btn_mostrar_todo = tk.Button(
            botones,
            text="📋 Mostrar todo",
            bg="#6c757d",
            fg=COLOR_BLANCO,
            relief="flat",
            font=("Segoe UI", escalar_fuente(9)),
            cursor="hand2",
            command=self.mostrar_todos,
            takefocus=1
        )
        self.btn_mostrar_todo.pack(side="left")

        self.aplicar_resalte_focus(self.entry_busqueda)
        self.aplicar_resalte_focus(self.entry_cantidad)
        self.aplicar_resalte_focus(self.entry_peso)

        self.aplicar_resalte_boton(self.btn_buscar, COLOR_SECUNDARIO)
        self.aplicar_resalte_boton(self.btn_agregar, "#28a745")
        self.aplicar_resalte_boton(self.btn_mostrar_todo, "#6c757d")


    # ============================================================
    # PANEL DE TICKET
    # ============================================================

    def crear_panel_ticket(self, parent):
        header_ticket = tk.Frame(parent, bg=COLOR_PRIMARIO, height=escalar(40))
        header_ticket.pack(fill="x")
        header_ticket.pack_propagate(False)

        tk.Label(
            header_ticket, text="🧾  TICKET ACTUAL",
            font=("Segoe UI", escalar_fuente(11), "bold"), fg=COLOR_BLANCO, bg=COLOR_PRIMARIO
        ).pack(side="left", padx=escalar(12), pady=escalar(8))

        self.lbl_items = tk.Label(
            header_ticket, text="0 líneas",
            font=("Segoe UI", escalar_fuente(9)), fg="#8ab4f8", bg=COLOR_PRIMARIO
        )
        self.lbl_items.pack(side="right", padx=escalar(12), pady=escalar(8))

        botones = tk.Frame(parent, bg="#f0f2f5")
        botones.pack(fill="x", padx=0, pady=0)

        self.btn_editar = tk.Button(
            botones, text="✏️ Editar", bg=COLOR_SECUNDARIO, fg=COLOR_BLANCO,
            relief="flat", font=("Segoe UI", escalar_fuente(8), "bold"), cursor="hand2",
            command=self.editar_linea_ticket, takefocus=1
        )
        self.btn_editar.pack(side="left", padx=(escalar(8), escalar(3)), pady=escalar(5))

        self.btn_eliminar = tk.Button(
            botones, text="🗑️ Eliminar", bg=COLOR_PELIGRO, fg=COLOR_BLANCO,
            relief="flat", font=("Segoe UI", escalar_fuente(8), "bold"), cursor="hand2",
            command=self.eliminar_linea_ticket, takefocus=1
        )
        self.btn_eliminar.pack(side="left", padx=escalar(3), pady=escalar(5))

        self.btn_vaciar = tk.Button(
            botones, text="❌ Vaciar", bg="#6c757d", fg=COLOR_BLANCO,
            relief="flat", font=("Segoe UI", escalar_fuente(8), "bold"), cursor="hand2",
            command=self.vaciar_ticket, takefocus=1
        )
        self.btn_vaciar.pack(side="left", padx=escalar(3), pady=escalar(5))

        self.aplicar_resalte_boton(self.btn_editar, COLOR_SECUNDARIO)
        self.aplicar_resalte_boton(self.btn_eliminar, COLOR_PELIGRO)
        self.aplicar_resalte_boton(self.btn_vaciar, "#6c757d")

        frame = tk.Frame(parent, bg=COLOR_BLANCO)
        frame.pack(fill="both", expand=True, padx=0, pady=0)

        style = ttk.Style()
        style.configure(
            "Ticket.Treeview",
            rowheight=max(36, escalar(52)),
            font=("Segoe UI", escalar_fuente(13))
        )
        style.configure(
            "Ticket.Treeview.Heading",
            font=("Segoe UI", escalar_fuente(12), "bold"),
            background="#e2e8f0",
            foreground="#333333",
            relief="flat"
        )

        columnas = ("producto", "cantidad", "precio", "total")

        self.tree_ticket = ttk.Treeview(
            frame,
            columns=columnas,
            show="headings",
            style="Ticket.Treeview"
        )

        self.tree_ticket.heading("producto", text="Producto")
        self.tree_ticket.heading("cantidad", text="Cant/Kg")
        self.tree_ticket.heading("precio", text="P.Unit")
        self.tree_ticket.heading("total", text="Total")

        self.tree_ticket.column("producto", width=escalar(140), minwidth=escalar(100), stretch=True, anchor="w")
        self.tree_ticket.column("cantidad", width=escalar(70), minwidth=escalar(50), stretch=False, anchor="center")
        self.tree_ticket.column("precio", width=escalar(115), minwidth=escalar(90), stretch=False, anchor="e")
        self.tree_ticket.column("total", width=escalar(130), minwidth=escalar(100), stretch=False, anchor="e")

        self.tree_ticket.tag_configure("ultimo", background="#e7f1ff")

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.tree_ticket.yview)
        self.tree_ticket.configure(yscrollcommand=scrollbar.set)

        self.tree_ticket.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree_ticket.bind("<Return>", lambda e: self.editar_linea_ticket())
        self.tree_ticket.bind("<Delete>", lambda e: self.eliminar_linea_ticket())
        self.tree_ticket.bind("<Double-1>", lambda e: self.editar_linea_ticket())
        self.tree_ticket.bind("<Right>", self.ir_desde_tabla_ticket_a_resumen)
        self.tree_ticket.bind("<Left>", self.ir_desde_tabla_ticket_a_zona_izquierda)


    # ============================================================
    # PANEL DE RESUMEN Y PAGO
    # ============================================================

    def crear_panel_resumen(self, parent):
        total_frame = tk.Frame(parent, bg="#002b5c", height=escalar(118))
        total_frame.pack(fill="x")
        total_frame.pack_propagate(False)

        tk.Label(
            total_frame, text="TOTAL",
            font=("Segoe UI", escalar_fuente(10), "bold"), fg="#8ab4f8", bg="#002b5c"
        ).pack(pady=(escalar(8), 0))

        self.lbl_total = tk.Label(
            total_frame, text="$ 0",
            font=("Segoe UI", escalar_fuente(30, minimo=22, maximo=32), "bold"), fg=COLOR_BLANCO, bg="#002b5c"
        )
        self.lbl_total.pack(pady=(0, 0))

        # Neto + IVA (precios sin IVA) o redondeo: el cajero ve por qué el
        # total no es la suma de las líneas.
        self.lbl_desglose = tk.Label(
            total_frame, text="", font=("Segoe UI", escalar_fuente(9)),
            fg="#8ab4f8", bg="#002b5c"
        )
        self.lbl_desglose.pack(pady=(0, escalar(4)))


        pago_section = tk.Frame(parent, bg=COLOR_BLANCO)
        pago_section.pack(fill="x", padx=escalar(15), pady=(escalar(15), escalar(5)))

        tk.Label(
            pago_section, text="💵  Pago del cliente:",
            font=("Segoe UI", escalar_fuente(10), "bold"), bg=COLOR_BLANCO, fg="#333"
        ).pack(anchor="w")

        self.entry_pago_cliente = tk.Entry(
            pago_section,
            font=("Segoe UI", escalar_fuente(20, minimo=15, maximo=22), "bold"),
            justify="center",
            takefocus=1
        )
        self.entry_pago_cliente.pack(fill="x", pady=(escalar(5), 0), ipady=escalar(5))
        self.entry_pago_cliente.bind("<KeyRelease>", lambda e: (formatear_con_miles(e), self.actualizar_vuelto()), add="+")

        vuelto_frame = tk.Frame(parent, bg="#e8f5e9")
        vuelto_frame.pack(fill="x", padx=escalar(15), pady=(escalar(10), escalar(5)))

        # Se guarda la referencia porque este bloque cambia a "FALTA" en rojo
        # cuando el pago del cliente no alcanza a cubrir el total.
        self.frame_vuelto = vuelto_frame
        self.lbl_vuelto_titulo = tk.Label(
            vuelto_frame, text="VUELTO",
            font=("Segoe UI", escalar_fuente(9), "bold"), bg="#e8f5e9", fg="#2e7d32"
        )
        self.lbl_vuelto_titulo.pack(pady=(escalar(8), 0))

        self.lbl_vuelto = tk.Label(
            vuelto_frame, text="$ 0",
            font=("Segoe UI", escalar_fuente(18, minimo=14, maximo=20), "bold"), bg="#e8f5e9", fg="#2e7d32"
        )
        self.lbl_vuelto.pack(pady=(0, escalar(8)))

        frame_botones_pago = tk.Frame(parent, bg=COLOR_BLANCO)
        frame_botones_pago.pack(fill="x", padx=escalar(15), pady=(escalar(10), escalar(5)))

        self.btn_pago_efectivo = tk.Button(
            frame_botones_pago,
            text="💵  COBRAR EFECTIVO",
            bg="#28a745",
            fg=COLOR_BLANCO,
            relief="flat",
            font=("Segoe UI", escalar_fuente(13, minimo=10, maximo=14), "bold"),
            cursor="hand2",
            height=2,
            command=lambda: self.confirmar_venta_ticket(metodo_pago="efectivo"),
            takefocus=1
        )
        self.btn_pago_efectivo.pack(fill="x", pady=(0, escalar(5)))

        frame_otros = tk.Frame(frame_botones_pago, bg=COLOR_BLANCO)
        frame_otros.pack(fill="x")
        frame_otros.grid_columnconfigure(0, weight=1, uniform="boton")
        frame_otros.grid_columnconfigure(1, weight=1, uniform="boton")

        self.btn_pago_tarjeta = tk.Button(
            frame_otros,
            text="💳 Tarjeta",
            bg="#17a2b8",
            fg=COLOR_BLANCO,
            relief="flat",
            font=("Segoe UI", escalar_fuente(10), "bold"),
            cursor="hand2",
            height=2,
            command=lambda: self.confirmar_venta_ticket(metodo_pago="tarjeta"),
            takefocus=1
        )
        self.btn_pago_tarjeta.grid(row=0, column=0, sticky="nsew", padx=(0, escalar(2)))

        self.btn_pago_transfer = tk.Button(
            frame_otros,
            text="📱 Transfer.",
            bg="#f39c12",
            fg=COLOR_BLANCO,
            relief="flat",
            font=("Segoe UI", escalar_fuente(10), "bold"),
            cursor="hand2",
            height=2,
            command=lambda: self.confirmar_venta_ticket(metodo_pago="transferencia"),
            takefocus=1
        )
        self.btn_pago_transfer.grid(row=0, column=1, sticky="nsew", padx=(escalar(2), 0))

        self.btn_cancelar = tk.Button(
            parent,
            text="❌  Cancelar / Limpiar",
            bg=COLOR_PELIGRO,
            fg=COLOR_BLANCO,
            relief="flat",
            font=("Segoe UI", escalar_fuente(9), "bold"),
            cursor="hand2",
            command=self.vaciar_ticket,
            takefocus=1
        )
        self.btn_cancelar.pack(fill="x", padx=escalar(15), pady=(escalar(10), escalar(15)))

        self.aplicar_resalte_focus(self.entry_pago_cliente)
        self.aplicar_resalte_boton(self.btn_pago_efectivo, "#28a745")
        self.aplicar_resalte_boton(self.btn_pago_tarjeta, "#17a2b8")
        self.aplicar_resalte_boton(self.btn_pago_transfer, "#f39c12")
        self.aplicar_resalte_boton(self.btn_cancelar, COLOR_PELIGRO)


# Milisegundos de espera antes de buscar mientras se escribe.
# Un lector de códigos de barras escribe ~13 caracteres en 100 ms: sin esta
# espera se disparaban 13 búsquedas (hasta 3 consultas cada una) por producto.
DEMORA_BUSQUEDA_MS = 250


def _buscar_en_vivo(self):
    """Programa la búsqueda y cancela la anterior si todavía no corrió."""
    _cancelar_busqueda_pendiente(self)
    self._busqueda_after_id = self.root.after(
        DEMORA_BUSQUEDA_MS, lambda: _ejecutar_busqueda_en_vivo(self)
    )


def _cancelar_busqueda_pendiente(self):
    pendiente = getattr(self, "_busqueda_after_id", None)
    if pendiente:
        try:
            self.root.after_cancel(pendiente)
        except Exception:
            # SILENCIO DELIBERADO: after_cancel falla si el temporizador ya
            # se disparó, que es un caso normal y esperado.
            pass
    self._busqueda_after_id = None


def _ejecutar_busqueda_en_vivo(self):
    self._busqueda_after_id = None

    # El módulo puede haberse cerrado mientras la búsqueda estaba en espera
    if not self.entry_busqueda or not self.entry_busqueda.winfo_exists():
        return

    texto = self.entry_busqueda.get().strip()
    if texto:
        self.buscar()
    else:
        self.mostrar_todos()
