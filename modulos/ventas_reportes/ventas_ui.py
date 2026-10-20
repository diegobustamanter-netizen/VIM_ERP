import tkinter as tk
from tkinter import ttk
from tkcalendar import DateEntry

from ui_scale import escalar, escalar_fuente

from config import (
    COLOR_PRIMARIO,
    COLOR_SECUNDARIO,
    COLOR_BLANCO,
    COLOR_GRIS,
    COLOR_PELIGRO,
    FUENTE_BOTON,
    FUENTE_MODULO
)


def construir_interfaz(self):
    for widget in self.frame_contenido.winfo_children():
        widget.destroy()

    parent = self.frame_contenido
    self._btn_activos_v = {}

    # ── Header ──────────────────────────────────────────
    header = tk.Frame(parent, bg=COLOR_PRIMARIO, height=escalar(70))
    header.pack(fill="x")
    header.pack_propagate(False)

    tk.Label(header, text="\U0001f4ca  VENTAS / REPORTES",
             font=FUENTE_MODULO, fg=COLOR_BLANCO, bg=COLOR_PRIMARIO
             ).pack(side="left", padx=escalar(20), pady=escalar(18))

    self.btn_cerrar = tk.Button(
        header, text="\u2190 Volver al Men\u00fa",
        bg=COLOR_PELIGRO, fg=COLOR_BLANCO, relief="flat",
        font=FUENTE_BOTON, cursor="hand2", command=self.volver_menu
    )
    self.btn_cerrar.pack(side="right", padx=escalar(20), pady=escalar(18))

    # ── Body: sidebar + contenido ────────────────────────
    body = tk.Frame(parent, bg=COLOR_GRIS)
    body.pack(fill="both", expand=True)

    # ── Sidebar
    sidebar = tk.Frame(body, bg="#f8fafc", width=max(240, escalar(280)))
    sidebar.pack(side="left", fill="y")
    sidebar.pack_propagate(False)

    tk.Frame(body, width=1, bg="#e2e8f0").pack(side="left", fill="y")

    # Área de contenido activo
    self.frame_panel_activo_v = tk.Frame(body, bg=COLOR_GRIS)
    self.frame_panel_activo_v.pack(side="left", fill="both", expand=True)

    # --- NUEVO: FILTROS GLOBALES (Arriba de los paneles) ---
    self.frame_filtros_globales = tk.Frame(self.frame_panel_activo_v, bg=COLOR_GRIS)
    self.frame_filtros_globales.pack(fill="x", padx=15, pady=(15, 0))
    crear_panel_filtros(self, self.frame_filtros_globales)

    # ── Pre-construir todos los paneles (ocultos) ────────
    self._paneles_v = {}

    p = tk.Frame(self.frame_panel_activo_v, bg=COLOR_GRIS)
    self._paneles_v["resumen"] = p
    _panel_resumen(self, p)

    p = tk.Frame(self.frame_panel_activo_v, bg=COLOR_GRIS)
    self._paneles_v["historial"] = p
    _panel_historial(self, p)

    p = tk.Frame(self.frame_panel_activo_v, bg=COLOR_BLANCO)
    self._paneles_v["ranking"] = p
    _panel_ranking(self, p)

    p = tk.Frame(self.frame_panel_activo_v, bg=COLOR_BLANCO)
    self._paneles_v["desempeno"] = p
    _panel_desempeno(self, p)

    p = tk.Frame(self.frame_panel_activo_v, bg=COLOR_BLANCO)
    self._paneles_v["visual"] = p
    _panel_visual(self, p)

    # ── Menú sidebar ─────────────────────────────────────
    tk.Label(sidebar, text="NAVEGACIÓN",
             font=("Segoe UI", escalar_fuente(10), "bold"), bg="#f8fafc", fg="#94a3b8"
             ).pack(anchor="w", padx=20, pady=(25, 10))


    secciones = [
        ("\U0001f4ca", "Resumen KPIs",       "resumen"),
        ("\U0001f9fe", "Historial Ventas",    "historial"),
        ("\U0001f3c6", "Ranking Negocio",     "ranking"),
        ("\u23f0",     "Desempeño",      "desempeno"),
        ("\U0001f4c8", "Análisis Visual","visual"),
    ]

    for icon, label, slug in secciones:
        _sidebar_btn(self, sidebar, icon, label, slug)

    _mostrar_panel_v(self, "resumen")
    self.aplicar_resalte_boton(self.btn_cerrar, COLOR_PELIGRO)


def _sidebar_btn(self, sidebar, icon, label, slug):
    btn = tk.Frame(sidebar, bg="#f8fafc", cursor="hand2")
    btn.pack(fill="x", padx=8, pady=2)

    tk.Label(btn, text=icon, font=("Segoe UI", escalar_fuente(13)), bg="#f8fafc",
             cursor="hand2", width=3).pack(side="left", pady=10, padx=(10, 4))
    lbl = tk.Label(btn, text=label, font=("Segoe UI", escalar_fuente(10)),
                   bg="#f8fafc", fg="#475569", cursor="hand2")
    lbl.pack(side="left", pady=10)

    def click(e, s=slug): _mostrar_panel_v(self, s)
    def enter(e, b=btn, l=lbl, s=slug):
        if not self._btn_activos_v.get(s):
            b.config(bg="#f1f5f9"); l.config(bg="#f1f5f9")
    def leave(e, b=btn, l=lbl, s=slug):
        if not self._btn_activos_v.get(s):
            b.config(bg="#f8fafc"); l.config(bg="#f8fafc")

    for w in (btn, lbl):
        w.bind("<Button-1>", click)
        w.bind("<Enter>", enter)
        w.bind("<Leave>", leave)

    self._btn_activos_v[slug] = False
    setattr(self, f"_vbtn_{slug}", (btn, lbl))


def _mostrar_panel_v(self, slug):
    try:
        # Check if app/root is being destroyed
        if not hasattr(self, 'root') or not self.root or not self.root.winfo_exists():
            return
        
        # Ocultar todos
        for s, frame in self._paneles_v.items():
            try:
                if frame.winfo_exists():
                    frame.pack_forget()
                self._btn_activos_v[s] = False
                b, l = getattr(self, f"_vbtn_{s}", (None, None))
                if b and b.winfo_exists() and l and l.winfo_exists():
                    b.config(bg="#f8fafc"); l.config(bg="#f8fafc", fg="#475569",
                                                      font=("Segoe UI", escalar_fuente(10)))
            except tk.TclError:
                pass  # Widget was destroyed

        # Mostrar activo
        if self._paneles_v[slug].winfo_exists():
            self._paneles_v[slug].pack(fill="both", expand=True)
        self._btn_activos_v[slug] = True
        b, l = getattr(self, f"_vbtn_{slug}", (None, None))
        if b and b.winfo_exists() and l and l.winfo_exists():
            b.config(bg="#e0f2fe"); l.config(bg="#e0f2fe", fg=COLOR_PRIMARIO,
                                              font=("Segoe UI", escalar_fuente(10), "bold"))

        if hasattr(self, '_set_panel_activo'):
            self._set_panel_activo(slug)
        if slug == 'visual' and hasattr(self, 'reportes_actuales') and self.reportes_actuales:
            self.renderizar_dashboard_graficos()
    except tk.TclError as e:
        pass  # Silently ignore Tcl errors during shutdown
    except Exception as e:
        pass  # Silently ignore other errors during shutdown






def crear_panel_filtros(self, parent):
    frame = tk.Frame(parent, bg=COLOR_BLANCO, bd=1, relief="solid")
    frame.pack(fill="x", pady=(0, 15), ipady=5)

    frame_atajos = tk.Frame(frame, bg=COLOR_BLANCO)
    frame_atajos.pack(fill="x", padx=15, pady=(8, 0))

    tk.Label(
        frame_atajos, text="Filtros Rápidos:",
        font=("Segoe UI", escalar_fuente(9), "bold"), bg=COLOR_BLANCO, fg="#666666"
    ).pack(side="left", padx=(0, 10))

    for texto, slug in (
        ("Hoy", "hoy"),
        ("Esta Semana", "semana"),
        ("Este Mes", "mes"),
        ("Este Año", "anio"),
    ):
        btn = tk.Button(
            frame_atajos, text=texto, bg="#e9ecef", fg="#333",
            relief="flat", font=("Segoe UI", escalar_fuente(9)), cursor="hand2",
            command=lambda s=slug: getattr(self, "set_fecha_rápida")(s)
        )
        btn.pack(side="left", padx=(0, 5), pady=2)
        setattr(self, f"btn_{slug}", btn)
        self.aplicar_resalte_fecha(btn)

    contenido = tk.Frame(frame, bg=COLOR_BLANCO)
    contenido.pack(fill="x", padx=15, pady=(8, 8))
    for col in range(8):
        contenido.grid_columnconfigure(col, weight=1 if col in (1, 3, 5, 7) else 0)

    tk.Label(contenido, text="Desde:", bg=COLOR_BLANCO, font=("Segoe UI", escalar_fuente(10), "bold")).grid(row=0, column=0, sticky="w", padx=(0, 5), pady=3)
    self.entry_fecha_desde = DateEntry(
        contenido, width=13, font=("Segoe UI", escalar_fuente(10)),
        locale='es_CL', date_pattern='dd-mm-yyyy',
        background='#002060', foreground='white',
        headersbackground='#002060', headersforeground='white',
        selectbackground='#17a2b8', selectforeground='white',
        normalbackground='white', normalforeground='black',
        weekendbackground='#f8f9fa', weekendforeground='#495057',
        borderwidth=1
    )
    self.entry_fecha_desde.grid(row=0, column=1, sticky="ew", padx=(0, 15), pady=3)

    tk.Label(contenido, text="Hasta:", bg=COLOR_BLANCO, font=("Segoe UI", escalar_fuente(10), "bold")).grid(row=0, column=2, sticky="w", padx=(0, 5), pady=3)
    self.entry_fecha_hasta = DateEntry(
        contenido, width=13, font=("Segoe UI", escalar_fuente(10)),
        locale='es_CL', date_pattern='dd-mm-yyyy',
        background='#002060', foreground='white',
        headersbackground='#002060', headersforeground='white',
        selectbackground='#17a2b8', selectforeground='white',
        normalbackground='white', normalforeground='black',
        weekendbackground='#f8f9fa', weekendforeground='#495057',
        borderwidth=1
    )
    self.entry_fecha_hasta.grid(row=0, column=3, sticky="ew", padx=(0, 15), pady=3)

    tk.Label(contenido, text="Filtro Folio:", bg=COLOR_BLANCO, font=("Segoe UI", escalar_fuente(10), "bold")).grid(row=0, column=4, sticky="w", padx=(0, 5), pady=3)
    self.entry_folio = tk.Entry(contenido, font=("Segoe UI", escalar_fuente(10)), width=15)
    self.entry_folio.grid(row=0, column=5, sticky="ew", padx=(0, 15), pady=3)

    tk.Label(contenido, text="Método:", bg=COLOR_BLANCO, font=("Segoe UI", escalar_fuente(10), "bold")).grid(row=0, column=6, sticky="w", padx=(0, 5), pady=3)
    self.combo_metodo = ttk.Combobox(
        contenido, values=["Todos", "Efectivo", "Tarjeta", "Transferencia"],
        state="readonly", width=15, font=("Segoe UI", escalar_fuente(10))
    )
    self.combo_metodo.current(0)
    self.combo_metodo.grid(row=0, column=7, sticky="ew", pady=3)

    self.btn_buscar = tk.Button(
        contenido, text="🔍 Buscar Ventas", bg=COLOR_SECUNDARIO,
        fg=COLOR_BLANCO, relief="flat", font=FUENTE_BOTON,
        cursor="hand2", command=self.buscar
    )
    self.btn_buscar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=(0, 5), pady=(8, 0))

    self.btn_exportar = tk.Button(
        contenido, text="📥 Centro de Descargas", bg="#17a2b8",
        fg=COLOR_BLANCO, relief="flat", font=FUENTE_BOTON,
        cursor="hand2", command=self.abrir_modal_exportacion
    )
    self.btn_exportar.grid(row=1, column=2, columnspan=3, sticky="ew", padx=5, pady=(8, 0))

    self.btn_limpiar = tk.Button(
        contenido, text="Limpiar Filtros", bg="#6c757d", fg=COLOR_BLANCO,
        relief="flat", font=FUENTE_BOTON, cursor="hand2",
        command=self.limpiar_filtros
    )
    self.btn_limpiar.grid(row=1, column=5, columnspan=3, sticky="ew", padx=(5, 0), pady=(8, 0))

    self.aplicar_resalte_focus(self.entry_folio)
    self.aplicar_resalte_boton(self.btn_buscar, COLOR_SECUNDARIO)
    self.aplicar_resalte_boton(self.btn_limpiar, "#6c757d")


def _armar_tab_historial(self, parent):
    top_bar = tk.Frame(parent, bg=COLOR_BLANCO)
    top_bar.pack(fill="x", padx=15, pady=(15, 8))

    tk.Label(top_bar, text="Historial de Transacciones (Doble clic para auditar la boleta)", font=("Segoe UI", escalar_fuente(11), "bold"), bg=COLOR_BLANCO, fg=COLOR_PRIMARIO).pack(side="left")

    self.btn_anular = tk.Button(
        top_bar,
        text="🚫 Anular Venta Seleccionada",
        bg=COLOR_PELIGRO,
        fg=COLOR_BLANCO,
        relief="flat",
        font=("Segoe UI", escalar_fuente(9), "bold"),
        cursor="hand2",
        command=self.solicitar_anulacion
    )
    self.btn_anular.pack(side="right")

    tabla_frame = tk.Frame(parent, bg=COLOR_BLANCO)
    tabla_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

    columnas = ("Folio", "Fecha / Hora", "Usuario", "Método", "Total", "Vuelto", "Estado")

    style = ttk.Style()
    style.configure("Ventas.Treeview", rowheight=escalar(35), font=("Segoe UI", escalar_fuente(11)), background="white", fieldbackground="white", borderwidth=0)
    style.configure("Ventas.Treeview.Heading", font=("Segoe UI", escalar_fuente(11), "bold"), background="#e2e8f0", foreground="#333333", relief="flat")

    self.tree_historial = ttk.Treeview(tabla_frame, columns=columnas, show="headings", style="Ventas.Treeview")
    self.tree_historial.tag_configure("impar", background="#edf2f7")
    self.tree_historial.tag_configure("par", background="#ffffff")

    for col in columnas:
        self.tree_historial.heading(col, text=col)

    self.tree_historial.column("Folio", width=escalar(180), anchor="center")
    self.tree_historial.column("Fecha / Hora", width=escalar(140), anchor="center")
    self.tree_historial.column("Usuario", width=escalar(120), anchor="center")
    self.tree_historial.column("Método", width=escalar(120), anchor="center")
    self.tree_historial.column("Total", width=escalar(100), anchor="e")
    self.tree_historial.column("Vuelto", width=escalar(100), anchor="e")
    self.tree_historial.column("Estado", width=escalar(120), anchor="center")

    scrollbar = ttk.Scrollbar(tabla_frame, orient="vertical", command=self.tree_historial.yview)
    self._historial_scrollbar = scrollbar
    self.tree_historial.configure(yscrollcommand=self._on_historial_scroll)
    self.tree_historial.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Loader con barra de progreso (indeterminada) para el historial
    self.frame_loader_historial = tk.Frame(tabla_frame, bg=COLOR_BLANCO,
                                           highlightbackground="#e2e8f0", highlightthickness=1)
    tk.Label(
        self.frame_loader_historial, text="⏳ Cargando ventas...",
        font=("Segoe UI", escalar_fuente(11), "bold"), bg=COLOR_BLANCO, fg="#475569"
    ).pack(padx=escalar(30), pady=(escalar(16), escalar(6)))
    self.pb_loader_historial = ttk.Progressbar(
        self.frame_loader_historial, mode="indeterminate", length=escalar(220)
    )
    self.pb_loader_historial.pack(padx=escalar(30), pady=(0, escalar(16)))

    self.tree_historial.bind("<Double-1>", lambda e: self.ver_detalle_venta())
    self.tree_historial.bind("<Return>", lambda e: self.ver_detalle_venta())


def _armar_tab_ranking(self, parent):
    frame_prod = tk.Frame(parent, bg=COLOR_BLANCO)
    frame_prod.pack(side="left", fill="both", expand=True, padx=(15, 5), pady=15)
    
    tk.Label(frame_prod, text="Top Productos (Rotación de Inventario)", font=("Segoe UI", escalar_fuente(11), "bold"), bg=COLOR_BLANCO, fg=COLOR_PRIMARIO).pack(anchor="w", pady=(0, 8))
    
    cols_p = ("#", "Producto", "Unidades", "Ingreso", "Utilidad")
    self.tree_ranking_prod = ttk.Treeview(frame_prod, columns=cols_p, show="headings", style="Ventas.Treeview")
    self.tree_ranking_prod.heading("#", text="#")
    self.tree_ranking_prod.heading("Producto", text="Producto")
    self.tree_ranking_prod.heading("Unidades", text="Und. Vendidas")
    self.tree_ranking_prod.heading("Ingreso", text="Bruto")
    self.tree_ranking_prod.heading("Utilidad", text="Utilidad")
    self.tree_ranking_prod.column("#", width=escalar(35), anchor="center")
    self.tree_ranking_prod.column("Producto", width=escalar(160), anchor="w")
    self.tree_ranking_prod.column("Unidades", width=escalar(80), anchor="center")
    self.tree_ranking_prod.column("Ingreso", width=escalar(90), anchor="e")
    self.tree_ranking_prod.column("Utilidad", width=escalar(90), anchor="e")
    
    vsp = ttk.Scrollbar(frame_prod, orient="vertical", command=self.tree_ranking_prod.yview)
    self.tree_ranking_prod.configure(yscrollcommand=vsp.set)
    self.tree_ranking_prod.pack(side="left", fill="both", expand=True)
    vsp.pack(side="right", fill="y")
    
    self.tree_ranking_prod.tag_configure("impar", background="#edf2f7")
    self.tree_ranking_prod.tag_configure("par", background="#ffffff")

    frame_cat = tk.Frame(parent, bg=COLOR_BLANCO)
    frame_cat.pack(side="right", fill="both", expand=True, padx=(5, 15), pady=15)
    
    tk.Label(frame_cat, text="Top Categorías (Sostén de Ingresos)", font=("Segoe UI", escalar_fuente(11), "bold"), bg=COLOR_BLANCO, fg=COLOR_PRIMARIO).pack(anchor="w", pady=(0, 8))
    
    cols_c = ("#", "Categoría", "Und", "Ingreso", "Utilidad")
    self.tree_ranking_cat = ttk.Treeview(frame_cat, columns=cols_c, show="headings", style="Ventas.Treeview")
    self.tree_ranking_cat.heading("#", text="#")
    self.tree_ranking_cat.heading("Categoría", text="Familia")
    self.tree_ranking_cat.heading("Und", text="Unidades")
    self.tree_ranking_cat.heading("Ingreso", text="Bruto")
    self.tree_ranking_cat.heading("Utilidad", text="Utilidad")
    self.tree_ranking_cat.column("#", width=escalar(35), anchor="center")
    self.tree_ranking_cat.column("Categoría", width=escalar(140), anchor="w")
    self.tree_ranking_cat.column("Und", width=escalar(60), anchor="center")
    self.tree_ranking_cat.column("Ingreso", width=escalar(90), anchor="e")
    self.tree_ranking_cat.column("Utilidad", width=escalar(90), anchor="e")
    
    vsc = ttk.Scrollbar(frame_cat, orient="vertical", command=self.tree_ranking_cat.yview)
    self.tree_ranking_cat.configure(yscrollcommand=vsc.set)
    self.tree_ranking_cat.pack(side="left", fill="both", expand=True)
    vsc.pack(side="right", fill="y")
    
    self.tree_ranking_cat.tag_configure("impar", background="#edf2f7")
    self.tree_ranking_cat.tag_configure("par", background="#ffffff")


def _armar_tab_horas(self, parent):
    tk.Label(parent, text="Flujo de Caja por Franja Horaria", font=("Segoe UI", escalar_fuente(11), "bold"), bg=COLOR_BLANCO, fg=COLOR_PRIMARIO).pack(anchor="w", padx=15, pady=(15, 8))

    frame_grid = tk.Frame(parent, bg=COLOR_BLANCO)
    frame_grid.pack(fill="both", expand=True, padx=15, pady=(0, 15))

    columnas = ("Hora", "Tickets Emitidos", "Flujo Generado")
    self.tree_horas = ttk.Treeview(frame_grid, columns=columnas, show="headings", style="Ventas.Treeview")
    self.tree_horas.tag_configure("impar", background="#edf2f7")
    self.tree_horas.tag_configure("par", background="#ffffff")

    self.tree_horas.heading("Hora", text="Tramo Horario")
    self.tree_horas.heading("Tickets Emitidos", text="Transacciones (Tickets)")
    self.tree_horas.heading("Flujo Generado", text="Total Facturado")
    
    self.tree_horas.column("Hora", width=escalar(120), anchor="center")
    self.tree_horas.column("Tickets Emitidos", width=escalar(150), anchor="center")
    self.tree_horas.column("Flujo Generado", width=escalar(150), anchor="center")

    scroll_h = ttk.Scrollbar(frame_grid, orient="vertical", command=self.tree_horas.yview)
    self.tree_horas.configure(yscrollcommand=scroll_h.set)
    self.tree_horas.pack(side="left", fill="both", expand=True)
    scroll_h.pack(side="right", fill="y")








def _armar_tab_graficos(self, parent):
    # Crear un canvas con scroll para que los gráficos tengan espacio
    canvas = tk.Canvas(parent, bg="#f8fafc", highlightthickness=0)
    scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    self.frame_graficos = tk.Frame(canvas, bg="#f8fafc")
    canvas_window = canvas.create_window((0, 0), window=self.frame_graficos, anchor="nw")

    def _on_resize(event):
        canvas.itemconfig(canvas_window, width=event.width)
    canvas.bind("<Configure>", _on_resize)
    self.frame_graficos.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    def _scroll(event):
        if canvas.winfo_exists():
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    canvas.bind_all("<MouseWheel>", _scroll)
    
    # Placeholder inicial estilizado + barra de progreso para cargas
    self.lbl_placeholder_graficos = tk.Label(
        self.frame_graficos,
        text="\U0001f4c8  Realice una búsqueda para generar el Análisis Visual Avanzado",
        font=("Segoe UI", escalar_fuente(13), "italic"),
        bg="#f8fafc", fg="#94a3b8"
    )
    self.lbl_placeholder_graficos.pack(pady=100)

    self.pb_loader_graficos = ttk.Progressbar(
        self.frame_graficos, mode="indeterminate", length=escalar(260)
    )
    # Se muestra solo durante cargas (ver _mostrar_placeholder_graficos)


# ============================================================
# WRAPPERS PARA SIDEBAR — llaman al código existente
# ============================================================

def _panel_resumen(self, parent):
    """Panel KPIs: Dashboard unificado con KPIs de ventas + Finanzas (P&L y Balance)."""
    # ── Contenedor principal con Scroll ──
    canvas = tk.Canvas(parent, bg=COLOR_GRIS, highlightthickness=0)
    scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    inner = tk.Frame(canvas, bg=COLOR_GRIS)
    canvas_window = canvas.create_window((0, 0), window=inner, anchor="nw")

    def _on_resize(event):
        canvas.itemconfig(canvas_window, width=event.width)
    canvas.bind("<Configure>", _on_resize)
    inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    # ── Rueda del mouse para el dashboard ──
    def _scroll_dash(event):
        if canvas.winfo_exists():
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    canvas.bind_all("<MouseWheel>", _scroll_dash)

    # ── CONTENIDO DEL DASHBOARD ──
    content = tk.Frame(inner, bg=COLOR_GRIS)
    content.pack(fill="both", expand=True, padx=15, pady=15)

    # 1. KPIs Rápidos de Ventas (RESTAURADOS)
    kpis_frame = tk.Frame(content, bg=COLOR_GRIS)
    kpis_frame.pack(fill="x", pady=(0, 15))
    
    def _card_kpi(parent, titulo, color, icon):
        f = tk.Frame(parent, bg=COLOR_BLANCO, bd=1, relief="solid")
        f.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        tk.Label(f, text=f"{icon} {titulo}", font=("Segoe UI", escalar_fuente(9), "bold"), bg=COLOR_BLANCO, fg="#64748b").pack(pady=(12, 0))
        lbl = tk.Label(f, text="$ 0", font=("Segoe UI", escalar_fuente(16), "bold"), bg=COLOR_BLANCO, fg=color)
        lbl.pack(pady=(5, 12))
        return lbl

    self.lbl_kpi_ventas_total = _card_kpi(kpis_frame, "VENTAS TOTALES", COLOR_PRIMARIO, "\U0001f4b0")
    self.lbl_kpi_ventas_efectivo = _card_kpi(kpis_frame, "TOTAL EFECTIVO", "#f39c12", "\U0001f4b5")
    self.lbl_kpi_ventas_tarjeta = _card_kpi(kpis_frame, "TOTAL TARJETA", "#17a2b8", "\U0001f4b3")
    self.lbl_kpi_ventas_transferencia = _card_kpi(kpis_frame, "TOTAL TRANSFERENCIA", "#28a745", "\U0001f504")

    # 3. Reportes Financieros (Layout de 2 columnas)
    fin_frame = tk.Frame(content, bg=COLOR_GRIS)
    fin_frame.pack(fill="both", expand=True)

    # Reutilizamos la lógica del layout financiero (P&L y Balance)
    # Creamos un frame que emule el 'inner' de finanzas pero sin canvas propio
    row = tk.Frame(fin_frame, bg=COLOR_GRIS)
    row.pack(fill="both", expand=True)

    # ── P&L ──
    f_pnl = tk.Frame(row, bg=COLOR_BLANCO, bd=1, relief="ridge")
    f_pnl.pack(side="left", fill="both", expand=True, padx=(0, 8))
    
    hdr_pnl = tk.Frame(f_pnl, bg=COLOR_PRIMARIO)
    hdr_pnl.pack(fill="x")
    tk.Label(hdr_pnl, text="ESTADO DE RESULTADOS (P&L)", font=("Segoe UI", escalar_fuente(11), "bold"), bg=COLOR_PRIMARIO, fg=COLOR_BLANCO).pack(anchor="w", padx=16, pady=10)
    
    body_pnl = tk.Frame(f_pnl, bg=COLOR_BLANCO)
    body_pnl.pack(fill="both", expand=True, padx=16, pady=12)

    # Filas de datos
    def linea(parent, texto, negrita=False, color="black", mostrar_pct=True):
        f = tk.Frame(parent, bg=COLOR_BLANCO)
        f.pack(fill="x", pady=2)
        peso = "bold" if negrita else "normal"
        lbl_txt = tk.Label(f, text=texto, font=("Segoe UI", escalar_fuente(9), peso), bg=COLOR_BLANCO, fg=color)
        lbl_txt.pack(side="left")

        lbl_pct = None
        if mostrar_pct:
            lbl_pct = tk.Label(f, text="", font=("Segoe UI", escalar_fuente(8)), bg=COLOR_BLANCO, fg="#aaa")
            lbl_pct.pack(side="right", padx=10)

        lbl_val = tk.Label(f, text="$ 0", font=("Segoe UI", escalar_fuente(9), peso), bg=COLOR_BLANCO, fg=color)
        lbl_val.pack(side="right")

        # Referencias a la fila y al texto: permiten renombrar u ocultar la
        # línea según el tipo de negocio sin cambiar cómo se llama a linea().
        lbl_val._fila = f
        lbl_val._lbl_texto = lbl_txt
        return lbl_val, lbl_pct

    self.lbl_pnl_ingresos, self.lbl_pnl_ingresos_pct = linea(body_pnl, "(+) Ventas Netas", negrita=True)
    self.lbl_pnl_iva_debito, _ = linea(body_pnl, "(+) IVA Débito", color="#6c757d", mostrar_pct=False)
    self.lbl_pnl_iva_credito, _ = linea(body_pnl, "(-) IVA Crédito", color="#6c757d", mostrar_pct=False)
    self.lbl_pnl_impuestos, self.lbl_pnl_impuestos_pct = linea(body_pnl, "(=) IVA a Pagar", negrita=True, color="#17a2b8")
    self.lbl_pnl_costos, self.lbl_pnl_costos_pct = linea(body_pnl, "(-) Costos Netos", color=COLOR_PELIGRO)

    self._sep_pnl = tk.Frame(body_pnl, height=1, bg="#dee2e6")
    self._sep_pnl.pack(fill="x", pady=6)
    self.lbl_pnl_utilidad_bruta, self.lbl_pnl_utilidad_bruta_pct = linea(body_pnl, "(=) UTILIDAD BRUTA", negrita=True, color="#28a745")

    self._lbl_titulo_gastos = tk.Label(body_pnl, text="GASTOS OPERATIVOS:", font=("Segoe UI", escalar_fuente(8), "bold"), bg=COLOR_BLANCO, fg="#666")
    self._lbl_titulo_gastos.pack(anchor="w", pady=(10, 2))
    self.frame_gastos_pnl = tk.Frame(body_pnl, bg=COLOR_BLANCO)
    self.frame_gastos_pnl.pack(fill="x")
    
    tk.Frame(body_pnl, height=2, bg=COLOR_PRIMARIO).pack(fill="x", pady=10)
    f_neto = tk.Frame(body_pnl, bg="#f8f9fa", padx=12, pady=10)
    f_neto.pack(fill="x")
    tk.Label(f_neto, text="UTILIDAD NETA", font=("Segoe UI", escalar_fuente(11), "bold"), bg="#f8f9fa").pack(side="left")
    self.lbl_pnl_utilidad_neta = tk.Label(f_neto, text="$ 0", font=("Segoe UI", escalar_fuente(13), "bold"), bg="#f8f9fa", fg="#28a745")
    self.lbl_pnl_utilidad_neta.pack(side="right")

    # ── BALANCE ──
    f_bal = tk.Frame(row, bg=COLOR_BLANCO, bd=1, relief="ridge", width=max(260, escalar(300)))
    f_bal.pack(side="left", fill="y", padx=(8, 0))
    f_bal.pack_propagate(False)

    hdr_bal = tk.Frame(f_bal, bg=COLOR_PRIMARIO)
    hdr_bal.pack(fill="x")
    tk.Label(hdr_bal, text="BALANCE GENERAL", font=("Segoe UI", escalar_fuente(11), "bold"), bg=COLOR_PRIMARIO, fg=COLOR_BLANCO).pack(anchor="w", padx=16, pady=10)

    body_bal = tk.Frame(f_bal, bg=COLOR_BLANCO)
    body_bal.pack(fill="both", expand=True, padx=16, pady=12)

    f_act = tk.Frame(body_bal, bg="#f0fdf4", padx=12, pady=10, highlightbackground="#bbf7d0", highlightthickness=1)
    f_act.pack(fill="x", pady=(0, 6))
    tk.Label(f_act, text="ACTIVOS", font=("Segoe UI", escalar_fuente(9), "bold"), bg="#f0fdf4", fg="#166534").pack(anchor="w")
    self.lbl_bal_inventario = tk.Label(f_act, text="Inventario: $ 0", bg="#f0fdf4", font=("Segoe UI", escalar_fuente(9)), fg="#166534"); self.lbl_bal_inventario.pack(anchor="w", pady=(4, 0))
    self.lbl_bal_efectivo = tk.Label(f_act, text="Efectivo: $ 0", bg="#f0fdf4", font=("Segoe UI", escalar_fuente(9)), fg="#166534"); self.lbl_bal_efectivo.pack(anchor="w")

    f_pas = tk.Frame(body_bal, bg="#fef2f2", padx=12, pady=10, highlightbackground="#fca5a5", highlightthickness=1)
    f_pas.pack(fill="x", pady=(0, 6))
    tk.Label(f_pas, text="PASIVOS", font=("Segoe UI", escalar_fuente(9), "bold"), bg="#fef2f2", fg="#991b1b").pack(anchor="w")
    self.lbl_bal_cuentas_pagar = tk.Label(f_pas, text="Deudas: $ 0", bg="#fef2f2", font=("Segoe UI", escalar_fuente(9)), fg="#991b1b"); self.lbl_bal_cuentas_pagar.pack(anchor="w", pady=(4, 0))

    tk.Frame(body_bal, height=1, bg="#dee2e6").pack(fill="x", pady=14)
    tk.Label(body_bal, text="PATRIMONIO ESTIMADO", font=("Segoe UI", escalar_fuente(9), "bold"), bg=COLOR_BLANCO).pack()
    self.lbl_bal_patrimonio = tk.Label(body_bal, text="$ 0", font=("Segoe UI", escalar_fuente(18), "bold"), bg=COLOR_BLANCO, fg=COLOR_PRIMARIO); self.lbl_bal_patrimonio.pack(pady=(4, 0))


def _panel_historial(self, parent):
    """Panel Historial: filtros completos + tabla de ventas."""
    inner = tk.Frame(parent, bg=COLOR_GRIS)
    inner.pack(fill="both", expand=True, padx=15, pady=15)
    # Tabla historial
    frame = tk.Frame(inner, bg=COLOR_BLANCO, bd=1, relief="solid")
    frame.pack(fill="both", expand=True)
    _armar_tab_historial(self, frame)


def _panel_ranking(self, parent):
    _armar_tab_ranking(self, parent)


def _panel_desempeno(self, parent):
    _armar_tab_horas(self, parent)



def _panel_visual(self, parent):
    _armar_tab_graficos(self, parent)
