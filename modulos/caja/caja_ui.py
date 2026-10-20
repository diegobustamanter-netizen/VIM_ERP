import tkinter as tk
from tkinter import ttk

from ui_scale import escalar, escalar_fuente

from config import COLOR_PRIMARIO, COLOR_BLANCO, COLOR_PELIGRO, FUENTE_BOTON, FUENTE_MODULO

from modulos.utils_globales import formatear_con_miles

# ─────────────────────────────────────────────────────────────
# PALETA AUXILIAR
# ─────────────────────────────────────────────────────────────
_BG_CARD      = "#ffffff"
_BG_PAGE      = "#f4f6f9"
_BG_SIDEBAR   = "#f0f4f8"
_BORDER       = "#e2e8f0"
_FG_MUTED     = "#64748b"
_FG_TITLE     = "#1e3a5f"
_FG_VALUE     = "#1e293b"

_COL_VERDE    = "#22c55e"
_COL_AZUL     = "#3b82f6"
_COL_NARANJA  = "#f97316"
_COL_CYAN     = "#06b6d4"
_COL_ROJO     = "#ef4444"


# ─────────────────────────────────────────────────────────────
# PUNTO DE ENTRADA
# ─────────────────────────────────────────────────────────────

def construir_ui(self):
    self.main_frame = tk.Frame(self.frame_contenido, bg=_BG_PAGE)
    self.main_frame.pack(fill="both", expand=True)

    _configurar_estilos()
    _crear_header(self)
    _crear_cuerpo(self)


# ─────────────────────────────────────────────────────────────
# ESTILOS
# ─────────────────────────────────────────────────────────────

def _configurar_estilos():
    style = ttk.Style()
    style.configure(
        "Caja.Treeview",
        rowheight=escalar(32),
        font=("Segoe UI", escalar_fuente(10)),
        borderwidth=0,
        background=_BG_CARD,
        fieldbackground=_BG_CARD,
    )
    style.configure(
        "Caja.Treeview.Heading",
        font=("Segoe UI", escalar_fuente(10), "bold"),
        background="#e2e8f0",
        foreground="#334155",
        relief="flat",
        padding=4,
    )
    style.map("Caja.Treeview.Heading", background=[("active", "#cbd5e1")])
    style.map(
        "Caja.Treeview",
        background=[("selected", "#dbeafe")],
        foreground=[("selected", "#1e3a5f")],
    )


# ─────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────

def _crear_header(self):
    hdr = tk.Frame(self.main_frame, bg=COLOR_PRIMARIO, height=escalar(68))
    hdr.pack(fill="x")
    hdr.pack_propagate(False)

    tk.Label(
        hdr, text="💰  CAJA",
        font=FUENTE_MODULO, fg=COLOR_BLANCO, bg=COLOR_PRIMARIO
    ).pack(side="left", padx=escalar(20), pady=escalar(18))

    tk.Label(
        hdr, text="Apertura, movimientos y cierre de caja",
        font=("Segoe UI", escalar_fuente(9)), bg=COLOR_PRIMARIO, fg="#a8c4e0"
    ).pack(side="left", pady=escalar(18))

    tk.Button(
        hdr, text="← Volver al Menú",
        font=FUENTE_BOTON,
        bg=COLOR_PELIGRO, fg=COLOR_BLANCO,
        relief="flat", bd=0, cursor="hand2",
        command=self.volver_menu,
    ).pack(side="right", padx=escalar(20), pady=escalar(18))


# ─────────────────────────────────────────────────────────────
# CUERPO PRINCIPAL
# ─────────────────────────────────────────────────────────────

def _crear_cuerpo(self):
    body = tk.Frame(self.main_frame, bg=_BG_PAGE)
    body.pack(fill="both", expand=True, padx=escalar(14), pady=escalar(14))
    body.grid_rowconfigure(0, weight=1)
    body.grid_columnconfigure(0, weight=0, minsize=max(180, escalar(210)))
    body.grid_columnconfigure(1, weight=1, minsize=max(300, escalar(450)))
    body.grid_columnconfigure(2, weight=0, minsize=max(230, escalar(280)))

    col1 = tk.Frame(body, bg=_BG_PAGE)
    col1.grid(row=0, column=0, sticky="ns")

    col3 = tk.Frame(body, bg=_BG_PAGE)
    col3.grid(row=0, column=2, sticky="nsew", padx=(escalar(12), 0))

    col2 = tk.Frame(body, bg=_BG_PAGE)
    col2.grid(row=0, column=1, sticky="nsew", padx=escalar(12))

    _panel_operacion(self, col1)
    _panel_estado(self, col2)
    _panel_movimientos(self, col2)
    _panel_resumen(self, col3)


# ─────────────────────────────────────────────────────────────
# PANELES
# ─────────────────────────────────────────────────────────────

def _panel_operacion(self, parent):
    card = _tarjeta(parent)
    card.pack(fill="x", pady=(0, escalar(10)))

    _titulo_seccion(card, "⚙️  OPERACIÓN")
    tk.Frame(card, height=1, bg=_BORDER).pack(fill="x", padx=escalar(14), pady=(0, escalar(10)))

    tk.Label(card, text="Monto inicial", font=("Segoe UI", escalar_fuente(9), "bold"),
             bg=_BG_CARD, fg=_FG_MUTED).pack(anchor="w", padx=escalar(14))

    entry_frame = tk.Frame(card, bg=_BG_CARD, highlightbackground=_BORDER, highlightthickness=1)
    entry_frame.pack(fill="x", padx=escalar(14), pady=(escalar(4), escalar(10)))

    tk.Label(entry_frame, text="$", font=("Segoe UI", escalar_fuente(12), "bold"), bg=_BG_CARD, fg=_FG_MUTED, width=2).pack(side="left", padx=(escalar(6), 0))

    self.entry_monto_inicial = tk.Entry(
        entry_frame, font=("Segoe UI", escalar_fuente(13), "bold"), justify="right", bd=0, relief="flat",
        bg=_BG_CARD, fg=_FG_VALUE, insertbackground=COLOR_PRIMARIO,
    )
    self.entry_monto_inicial.pack(side="left", fill="both", expand=True, ipady=escalar(6), padx=(0, escalar(8)))
    self.entry_monto_inicial.insert(0, "0")
    self.entry_monto_inicial.bind("<KeyRelease>", formatear_con_miles, add="+")

    btn_frame = tk.Frame(card, bg=_BG_CARD)
    btn_frame.pack(fill="x", padx=escalar(14), pady=(0, escalar(14)))

    self.btn_abrir_caja = _boton_accion(btn_frame, "🏦  Abrir Caja", COLOR_PRIMARIO, self.abrir_caja_real)
    self.btn_abrir_caja.pack(fill="x", pady=(0, escalar(6)))

    self.btn_ingreso = _boton_accion(btn_frame, "➕  Ingreso", "#16a34a", self.registrar_ingreso, state="disabled")
    self.btn_ingreso.pack(fill="x", pady=escalar(6))

    self.btn_egreso = _boton_accion(btn_frame, "➖  Egreso", "#dc2626", self.registrar_egreso, state="disabled")
    self.btn_egreso.pack(fill="x", pady=escalar(6))

    self.btn_cerrar_caja = _boton_accion(btn_frame, "🔒  Cerrar Caja", "#374151", self.cerrar_caja_real, state="disabled")
    self.btn_cerrar_caja.pack(fill="x", pady=(escalar(6), 0))


def _panel_estado(self, parent):
    card = _tarjeta(parent)
    card.pack(fill="x", pady=(0, escalar(10)))

    _titulo_seccion(card, "📊  ESTADO ACTUAL")
    tk.Frame(card, height=1, bg=_BORDER).pack(fill="x", padx=escalar(14), pady=(0, escalar(10)))

    chips_row = tk.Frame(card, bg=_BG_CARD)
    chips_row.pack(fill="x", padx=escalar(14), pady=(0, escalar(14)))
    for i in range(4): chips_row.grid_columnconfigure(i, weight=1, uniform="chip")

    self.lbl_estado_valor = _chip_estado(chips_row, 0, "●", "#dcfce7", "#15803d", "Estado", "Cerrada", "#dc2626")
    self.lbl_usuario_valor = _chip_estado(chips_row, 1, "👤", "#dbeafe", "#1d4ed8", "Usuario", "-")
    self.lbl_fecha_apertura_valor = _chip_estado(chips_row, 2, "📅", "#f3e8ff", "#7e22ce", "Apertura", "-")
    self.lbl_monto_inicial_valor = _chip_estado(chips_row, 3, "💼", "#fff7ed", "#c2410c", "Fondo Inicial", "$ 0")


def _panel_movimientos(self, parent):
    card = _tarjeta(parent)
    card.pack(fill="both", expand=True)

    _titulo_seccion(card, "📋  MOVIMIENTOS DE CAJA")
    tk.Frame(card, height=1, bg=_BORDER).pack(fill="x", padx=escalar(14), pady=(0, escalar(8)))

    tabla_wrap = tk.Frame(card, bg=_BG_CARD)
    tabla_wrap.pack(fill="both", expand=True, padx=escalar(14), pady=(0, escalar(14)))

    columnas = ("Hora", "Movimiento", "Referencia", "Monto", "Descripción")
    self.tree_movimientos = ttk.Treeview(tabla_wrap, columns=columnas, show="headings", height=10, style="Caja.Treeview")
    
    anchos = {"Hora": escalar(75), "Movimiento": escalar(140), "Referencia": escalar(100), "Monto": escalar(100), "Descripción": escalar(250)}
    for col in columnas:
        self.tree_movimientos.heading(col, text=col)
        self.tree_movimientos.column(col, width=anchos.get(col, 100), anchor="center" if col != "Monto" else "e")

    scrollbar = ttk.Scrollbar(tabla_wrap, orient="vertical", command=self.tree_movimientos.yview)
    self.tree_movimientos.configure(yscrollcommand=scrollbar.set)
    self.tree_movimientos.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")


def _panel_resumen(self, parent):
    card = _tarjeta(parent)
    card.pack(fill="both", expand=True)

    _titulo_seccion(card, "💰  RESUMEN")
    tk.Frame(card, height=1, bg=_BORDER).pack(fill="x", padx=escalar(14), pady=(0, escalar(10)))

    container = tk.Frame(card, bg=_BG_CARD)
    container.pack(fill="both", expand=True, padx=escalar(10), pady=(0, escalar(10)))

    self.lbl_ventas_efectivo_valor = _mini_card(container, "💵", _COL_VERDE, "#dcfce7", "Ventas Efectivo", "$ 0")
    self.lbl_ventas_tarjeta_valor = _mini_card(container, "💳", _COL_AZUL, "#dbeafe", "Ventas Tarjeta", "$ 0")
    self.lbl_ventas_transferencia_valor = _mini_card(container, "🔁", _COL_NARANJA, "#ffedd5", "Transferencias", "$ 0")
    self.lbl_ingresos_valor = _mini_card(container, "📈", _COL_CYAN, "#cffafe", "Ingresos Extras", "$ 0")
    self.lbl_egresos_valor = _mini_card(container, "📉", _COL_ROJO, "#fee2e2", "Egresos / Gastos", "$ 0")
    
    tk.Frame(container, height=1, bg=_BORDER).pack(fill="x", pady=escalar(10))
    self.lbl_efectivo_esperado_valor = _mini_card_destacado(container, "💼", "Efectivo Esperado", "$ 0")


# ─────────────────────────────────────────────────────────────
# COMPONENTES
# ─────────────────────────────────────────────────────────────

def _tarjeta(parent):
    return tk.Frame(parent, bg=_BG_CARD, bd=0, highlightbackground=_BORDER, highlightthickness=1)

def _titulo_seccion(parent, texto):
    tk.Label(parent, text=texto, font=("Segoe UI", escalar_fuente(10), "bold"), bg=_BG_CARD, fg=_FG_TITLE).pack(anchor="w", padx=escalar(14), pady=(escalar(12), escalar(6)))

def _boton_accion(parent, texto, color, comando=None, state="normal"):
    return tk.Button(parent, text=texto, font=("Segoe UI", escalar_fuente(9), "bold"), bg=color, fg=COLOR_BLANCO, relief="flat", pady=escalar(8), cursor="hand2", command=comando, state=state)

def _chip_estado(parent, col, icono, bg_icono, fg_icono, titulo, valor, color_valor="#1e293b"):
    card = tk.Frame(parent, bg=_BG_CARD, highlightbackground=_BORDER, highlightthickness=1)
    card.grid(row=0, column=col, padx=escalar(4), pady=escalar(4), sticky="nsew")
    tk.Label(card, text=icono, font=("Segoe UI", escalar_fuente(18)), bg=bg_icono, fg=fg_icono).pack(pady=(escalar(10), escalar(2)), padx=escalar(10), fill="x")
    tk.Label(card, text=titulo, font=("Segoe UI", escalar_fuente(8)), bg=_BG_CARD, fg=_FG_MUTED).pack()
    # Sin width fijo: con width=10 textos como "Administrador" o la fecha
    # de apertura quedaban recortados por ambos lados.
    lbl = tk.Label(card, text=valor, font=("Segoe UI", escalar_fuente(10), "bold"), bg=_BG_CARD, fg=color_valor)
    lbl.pack(pady=(escalar(2), escalar(10)), padx=escalar(6), fill="x")
    return lbl

def _mini_card(parent, icono, color_icono, bg_icono, titulo, valor):
    card = tk.Frame(parent, bg=_BG_CARD)
    card.pack(fill="x", pady=escalar(2))
    inner = tk.Frame(card, bg=_BG_CARD, padx=escalar(8), pady=escalar(6))
    inner.pack(fill="x")
    ic_frame = tk.Frame(inner, bg=bg_icono, width=escalar(32), height=escalar(32))
    ic_frame.pack(side="left")
    ic_frame.pack_propagate(False)
    tk.Label(ic_frame, text=icono, font=("Segoe UI", escalar_fuente(11)), bg=bg_icono, fg=color_icono).pack(expand=True)
    info = tk.Frame(inner, bg=_BG_CARD)
    info.pack(side="left", fill="both", expand=True, padx=(escalar(10), 0))
    tk.Label(info, text=titulo, font=("Segoe UI", escalar_fuente(8), "bold"), bg=_BG_CARD, fg=_FG_MUTED, anchor="w").pack(fill="x")
    lbl_val = tk.Label(info, text=valor, font=("Segoe UI", escalar_fuente(11), "bold"), bg=_BG_CARD, fg=_FG_VALUE, anchor="w", width=12)
    lbl_val.pack(fill="x")
    return lbl_val

def _mini_card_destacado(parent, icono, titulo, valor):
    card = tk.Frame(parent, bg="#1e293b", padx=escalar(12), pady=escalar(12))
    card.pack(fill="x", pady=escalar(5))
    ic_lbl = tk.Label(card, text=icono, font=("Segoe UI", escalar_fuente(16)), bg="#334155", fg="white", width=2)
    ic_lbl.pack(side="left")
    info = tk.Frame(card, bg="#1e293b")
    info.pack(side="left", fill="both", expand=True, padx=(escalar(12), 0))
    tk.Label(info, text=titulo.upper(), font=("Segoe UI", escalar_fuente(7), "bold"), bg="#1e293b", fg="#94a3b8", anchor="w").pack(fill="x")
    lbl_val = tk.Label(info, text=valor, font=("Segoe UI", escalar_fuente(13), "bold"), bg="#1e293b", fg="#f8fafc", anchor="w", width=12)
    lbl_val.pack(fill="x")
    return lbl_val
