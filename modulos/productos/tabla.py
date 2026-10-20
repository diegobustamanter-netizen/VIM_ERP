import tkinter as tk
from tkinter import ttk

from config import (
    COLOR_PRIMARIO,
    COLOR_SECUNDARIO,
    COLOR_BLANCO,
    FUENTE_BOTON
)
from database import listar_productos
from ui_scale import escalar, escalar_fuente


class ProductosTablaMixin:
    def crear_panel_derecho(self, parent):
        top = tk.Frame(parent, bg=COLOR_BLANCO)
        top.pack(fill="x", padx=escalar(15), pady=(escalar(15), escalar(5)))

        tk.Label(
            top,
            text="Listado de Productos",
            font=("Segoe UI", escalar_fuente(16), "bold"),
            bg=COLOR_BLANCO,
            fg=COLOR_PRIMARIO
        ).pack(side="left")

        buscador = tk.Frame(parent, bg=COLOR_BLANCO)
        buscador.pack(fill="x", padx=escalar(15), pady=(0, escalar(10)))

        tk.Label(
            buscador,
            text="Buscar por código, PLU o nombre:",
            bg=COLOR_BLANCO,
            fg="black",
            font=("Segoe UI", escalar_fuente(10), "bold")
        ).pack(side="left", padx=(0, 10))

        self.entry_buscar = tk.Entry(buscador, font=("Segoe UI", escalar_fuente(10)), width=35)
        self.entry_buscar.pack(side="left", padx=(0, 10))
        self.entry_buscar.bind("<KeyRelease>", self.buscar_productos)

        tk.Button(
            buscador,
            text="Mostrar Todos",
            bg=COLOR_SECUNDARIO,
            fg=COLOR_BLANCO,
            relief="flat",
            font=FUENTE_BOTON,
            cursor="hand2",
            command=self.mostrar_todos
        ).pack(side="left")

        self.lbl_total = tk.Label(
            parent,
            text="Total productos: 0",
            bg=COLOR_BLANCO,
            fg=COLOR_PRIMARIO,
            font=("Segoe UI", escalar_fuente(10), "bold")
        )
        self.lbl_total.pack(anchor="w", padx=escalar(15), pady=(0, escalar(8)))

        self.crear_tabla(parent)

    def crear_tabla(self, parent):
        frame_tabla = tk.Frame(
            parent,
            bg=COLOR_BLANCO,
            highlightthickness=1,
            highlightbackground="#e2e8f0"
        )
        frame_tabla.pack(fill="both", expand=True, padx=escalar(15), pady=(0, escalar(15)))

        columnas = (
            "id",
            "codigo_barras",
            "codigo_pos",
            "nombre",
            "tipo_item",
            "tipo_venta",
            "precio_venta",
            "precio_kilo",
            "stock",
            "stock_minimo",
        )

        style = ttk.Style()
        style.configure(
            "ProductosPrincipal.Treeview.Heading",
            font=("Segoe UI", escalar_fuente(10), "bold"),
            background="#f1f5f9",
            foreground="#334155",
            relief="flat",
            padding=escalar(6)
        )
        style.map(
            "ProductosPrincipal.Treeview.Heading",
            background=[("active", "#cbd5e1")]
        )

        style.configure(
            "ProductosPrincipal.Treeview",
            rowheight=escalar(32),
            font=("Segoe UI", escalar_fuente(10)),
            background=COLOR_BLANCO,
            fieldbackground=COLOR_BLANCO,
            borderwidth=0,
        )
        style.map(
            "ProductosPrincipal.Treeview",
            background=[("selected", "#dbeafe")],
            foreground=[("selected", "#1e3a5f")]
        )

        self.tree = ttk.Treeview(
            frame_tabla,
            columns=columnas,
            show="headings",
            height=18,
            style="ProductosPrincipal.Treeview"
        )

        self.tree.heading("id", text="ID")
        self.tree.heading("codigo_barras", text="Cod. Barras")
        self.tree.heading("codigo_pos", text="Cod. POS")
        self.tree.heading("nombre", text="Nombre")
        self.tree.heading("tipo_item", text="Ítem")
        self.tree.heading("tipo_venta", text="Venta")
        self.tree.heading("precio_venta", text="Precio")
        self.tree.heading("precio_kilo", text="Precio/Kg")
        self.tree.heading("stock", text="Stock")
        self.tree.heading("stock_minimo", text="Stock Mín.")

        self.tree.column("id", width=escalar(55), anchor="center", stretch=False)
        self.tree.column("codigo_barras", width=escalar(130), anchor="center", stretch=False)
        self.tree.column("codigo_pos", width=escalar(90), anchor="center", stretch=False)
        self.tree.column("nombre", width=escalar(250), anchor="w")
        self.tree.column("tipo_item", width=escalar(80), anchor="center", stretch=False)
        self.tree.column("tipo_venta", width=escalar(80), anchor="center", stretch=False)
        self.tree.column("precio_venta", width=escalar(100), anchor="e", stretch=False)
        self.tree.column("precio_kilo", width=escalar(100), anchor="e", stretch=False)
        self.tree.column("stock", width=escalar(90), anchor="center", stretch=False)
        self.tree.column("stock_minimo", width=escalar(105), anchor="center", stretch=False)

        scrollbar_y = ttk.Scrollbar(frame_tabla, orient="vertical", command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(frame_tabla, orient="horizontal", command=self.tree.xview)

        self.tree.configure(
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set
        )

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")

        frame_tabla.grid_rowconfigure(0, weight=1)
        frame_tabla.grid_columnconfigure(0, weight=1)

        self.tree.tag_configure("stock_bajo", background="#fef2f2", foreground="#b91c1c")

    def cargar_productos(self, filtro=""):
        if not self.tree:
            return

        self.tree.delete(*self.tree.get_children())

        try:
            productos = listar_productos()
        except Exception:
            productos = []

        filtro = (filtro or "").strip().lower()

        if filtro:
            productos = [
                p for p in productos
                if filtro in str(p.get("nombre") or "").lower()
                or filtro in str(p.get("codigo_barras") or "").lower()
                or filtro in str(p.get("codigo_pos") or "").lower()
            ]

        for producto in productos:
            stock = float(producto.get("stock") or 0)
            stock_minimo = float(producto.get("stock_minimo") or 0)
            tipo_item = producto.get("tipo_item") or "producto"

            tags = ("stock_bajo",) if tipo_item != "servicio" and stock <= stock_minimo else ()

            precio_unidad_valor = float(producto.get("precio_venta") or 0)
            precio_kilo_valor = float(producto.get("precio_por_kilo") or 0)

            precio_unidad = self.formatear_moneda(precio_unidad_valor) if precio_unidad_valor > 0 else "-"
            precio_kilo = self.formatear_moneda(precio_kilo_valor) if precio_kilo_valor > 0 else "-"

            if tipo_item == "servicio":
                stock_str = "N/A"
                stock_minimo_str = "N/A"
            else:
                stock_str = self.formatear_numero(stock)
                stock_minimo_str = self.formatear_numero(stock_minimo)

            self.tree.insert(
                "",
                "end",
                values=(
                    producto.get("id", ""),
                    producto.get("codigo_barras") or "",
                    producto.get("codigo_pos") or "",
                    producto.get("nombre") or "",
                    tipo_item,
                    producto.get("tipo_venta") or "unidad",
                    precio_unidad,
                    precio_kilo,
                    stock_str,
                    stock_minimo_str,
                ),
                tags=tags
            )

        if self.lbl_total:
            self.lbl_total.config(text=f"Total productos: {len(productos)}")

    def buscar_productos(self, event=None):
        filtro = self.entry_buscar.get().strip() if self.entry_buscar else ""
        self.cargar_productos(filtro)

    def mostrar_todos(self):
        if self.entry_buscar:
            self.entry_buscar.delete(0, tk.END)
        self.cargar_productos("")