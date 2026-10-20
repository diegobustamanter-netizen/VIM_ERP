import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime

from ui_scale import escalar, escalar_fuente
from config import (
    COLOR_PRIMARIO, COLOR_SECUNDARIO, COLOR_BLANCO, COLOR_GRIS, 
    COLOR_PELIGRO, FUENTE_BOTON, FUENTE_MODULO
)
from modulos.utils_globales import limpiar_formato_numerico, formatear_con_miles, formatear_rut, aplicar_barra_windows_azul, centrar_ventana_mejorado, preparar_modal_scrollable
from database.historial import registrar_historial
from modulos.seguridad.sesion import Sesion
from vim_logger import get_logger

def _fmt_fecha(fecha_str):
    """Convierte AAAA-MM-DD (o con hora) a DD-MM-AAAA para mostrar en tablas."""
    try:
        s = str(fecha_str)[:10]
        y, m, d = s.split("-")
        return f"{d}-{m}-{y}"
    except Exception:
        return str(fecha_str)[:10]

def construir_interfaz(self):
    """
    Construye la interfaz principal del módulo de Compras, Gastos y Finanzas con Sidebar.
    """
    for widget in self.frame_contenido.winfo_children():
        widget.destroy()

    self.btn_activos_erp = {}
    self.paneles_erp = {}

    # Header
    header = tk.Frame(self.frame_contenido, bg=COLOR_PRIMARIO, height=escalar(70))
    header.pack(fill="x")
    header.pack_propagate(False)

    tk.Label(
        header, text="🛍️  ADMINISTRACIÓN", 
        font=FUENTE_MODULO, fg=COLOR_BLANCO, bg=COLOR_PRIMARIO
    ).pack(side="left", padx=escalar(20), pady=escalar(18))

    tk.Button(
        header, text="← Volver al Menú", bg=COLOR_PELIGRO, fg=COLOR_BLANCO,
        relief="flat", font=FUENTE_BOTON, cursor="hand2",
        command=self.volver_menu
    ).pack(side="right", padx=escalar(20), pady=escalar(18))

    # Contenedor Principal (Sidebar + Contenido)
    cuerpo = tk.Frame(self.frame_contenido, bg=COLOR_GRIS)
    cuerpo.pack(fill="both", expand=True)

    # Sidebar
    sidebar = tk.Frame(cuerpo, bg="#f8fafc", width=max(240, escalar(280)), bd=0) # Slate 50
    sidebar.pack(side="left", fill="y", padx=0, pady=0)
    sidebar.pack_propagate(False)

    # Borde sutil a la derecha del sidebar
    tk.Frame(cuerpo, width=1, bg="#e2e8f0").pack(side="left", fill="y")

    tk.Label(sidebar, text="NAVEGACIÓN", font=("Segoe UI", escalar_fuente(10), "bold"), bg="#f8fafc", fg="#94a3b8").pack(anchor="w", padx=escalar(20), pady=(escalar(30), escalar(15)))

    # Panel Central de Contenido (Único contenedor activo)
    self.panel_central_erp = tk.Frame(cuerpo, bg=COLOR_GRIS)
    self.panel_central_erp.pack(side="left", fill="both", expand=True, padx=max(10, escalar(20)), pady=max(10, escalar(20)))

    # Definición de Secciones
    self.secciones_erp = [
        ("📝", "Registro", "registro"),
        ("⏳", "Cuentas Pagar", "cuentas_pagar"),
        ("👥", "Personal", "empleados"),
        ("🏭", "Proveedores", "proveedores"),
        ("📊", "Plan de Cuentas", "config_cuentas")
    ]

    # Construir Menú
    for icon, texto, slug in self.secciones_erp:
        btn = tk.Frame(sidebar, bg="#f8fafc", cursor="hand2")
        btn.pack(fill="x", padx=8, pady=2)
        
        lbl_icon = tk.Label(btn, text=icon, font=("Segoe UI", escalar_fuente(13)), bg="#f8fafc", cursor="hand2", width=3)
        lbl_icon.pack(side="left", pady=10, padx=(12, 4))
        
        lbl_text = tk.Label(btn, text=texto, font=("Segoe UI", escalar_fuente(10)), bg="#f8fafc", fg="#475569", cursor="hand2")
        lbl_text.pack(side="left", pady=10)
        
        # Eventos con closures correctos
        def create_handler(s):
            return lambda e: cambiar_seccion_erp(self, s)
        
        def create_enter(s, b, lt, li):
            return lambda e: on_enter_sidebar(self, s, b, lt, li)
            
        def create_leave(s, b, lt, li):
            return lambda e: on_leave_sidebar(self, s, b, lt, li)

        for w in (btn, lbl_icon, lbl_text):
            w.bind("<Button-1>", create_handler(slug))
            w.bind("<Enter>", create_enter(slug, btn, lbl_text, lbl_icon))
            w.bind("<Leave>", create_leave(slug, btn, lbl_text, lbl_icon))
            
        self.btn_activos_erp[slug] = False
        setattr(self, f"_btn_erp_{slug}", (btn, lbl_icon, lbl_text))

    # Crear los frames para cada sección
    self.tab_registro = tk.Frame(self.panel_central_erp, bg=COLOR_GRIS)
    self.tab_cuentas_pagar = tk.Frame(self.panel_central_erp, bg=COLOR_GRIS)
    self.tab_empleados = tk.Frame(self.panel_central_erp, bg=COLOR_GRIS)
    self.tab_proveedores = tk.Frame(self.panel_central_erp, bg=COLOR_GRIS)
    self.tab_config_cuentas = tk.Frame(self.panel_central_erp, bg=COLOR_GRIS)

    self.paneles_erp = {
        "registro": self.tab_registro,
        "cuentas_pagar": self.tab_cuentas_pagar,
        "empleados": self.tab_empleados,
        "proveedores": self.tab_proveedores,
        "config_cuentas": self.tab_config_cuentas
    }

    # Estilizar tablas
    estilizar_tablas()

    # Inicializar contenido de cada frame
    inicializar_tab_registro(self)
    inicializar_tab_cuentas_pagar(self)
    inicializar_tab_empleados(self)
    inicializar_tab_proveedores(self)
    inicializar_tab_config_cuentas(self)

    # Mostrar la primera sección por defecto
    cambiar_seccion_erp(self, "registro")

def cambiar_seccion_erp(self, slug):
    """Cambia la sección visible en el panel central."""
    # Ocultar todos los paneles
    for p in self.paneles_erp.values():
        p.pack_forget()
    
    # Mostrar el seleccionado
    self.paneles_erp[slug].pack(fill="both", expand=True)
    
    # Actualizar sidebar
    marcar_activo_erp(self, slug)
    
    # Ejecutar refrescos si es necesario
    if slug == "registro":
        refrescar_combos_maestros(self)
        actualizar_recientes_compras(self)
    elif slug == "cuentas_pagar":
        actualizar_tabla_deudas(self)
    elif slug == "empleados":
        actualizar_tabla_empleados(self)
        actualizar_tabla_liquidaciones(self)
    elif slug == "proveedores":
        actualizar_tabla_proveedores_erp(self)
    elif slug == "config_cuentas":
        actualizar_tabla_cuentas(self)

def marcar_activo_erp(self, slug_activo):
    """Resalta visualmente el botón activo en el sidebar."""
    for slug in self.btn_activos_erp.keys():
        self.btn_activos_erp[slug] = (slug == slug_activo)
        b, li, lt = getattr(self, f"_btn_erp_{slug}")
        
        if slug == slug_activo:
            b.config(bg="#e0f2fe") # Sky 100
            li.config(bg="#e0f2fe", fg=COLOR_PRIMARIO)
            lt.config(bg="#e0f2fe", fg=COLOR_PRIMARIO, font=("Segoe UI", escalar_fuente(10), "bold"))
        else:
            b.config(bg="#f8fafc") # Slate 50
            li.config(bg="#f8fafc", fg="#475569")
            lt.config(bg="#f8fafc", fg="#475569", font=("Segoe UI", escalar_fuente(10)))

def on_enter_sidebar(self, slug, b, lt, li):
    if not self.btn_activos_erp.get(slug, False):
        b.config(bg="#f1f5f9") # Slate 100
        lt.config(bg="#f1f5f9")
        li.config(bg="#f1f5f9")

def on_leave_sidebar(self, slug, b, lt, li):
    if not self.btn_activos_erp.get(slug, False):
        b.config(bg="#f8fafc") # Slate 50
        lt.config(bg="#f8fafc")
        li.config(bg="#f8fafc")

def estilizar_tablas():
    style = ttk.Style()
    style.configure(
        "ERP.Treeview.Heading",
        font=("Segoe UI", escalar_fuente(10), "bold"),
        background="#e2e8f0",
        foreground="#333333",
        relief="flat"
    )
    style.map("ERP.Treeview.Heading", background=[("active", "#cbd5e1")])
    style.configure("ERP.Treeview", rowheight=escalar(30), font=("Segoe UI", escalar_fuente(10)))

def render_tarjeta_erp(parent, titulo):
    """Utilidad visual para crear un panel blanco tipo tarjeta con estilo moderno."""
    frame = tk.Frame(parent, bg=COLOR_BLANCO, bd=0, highlightthickness=1, highlightbackground="#e2e8f0")
    frame.pack(fill="both", expand=True)
    
    # Header de la tarjeta
    header = tk.Frame(frame, bg=COLOR_BLANCO)
    header.pack(fill="x", padx=20, pady=(15, 5))
    
    tk.Label(header, text=titulo, font=("Segoe UI", escalar_fuente(12), "bold"), bg=COLOR_BLANCO, fg=COLOR_PRIMARIO).pack(side="left")
    
    # Divisor sutil
    tk.Frame(frame, height=1, bg="#f1f5f9").pack(fill="x", padx=20, pady=(5, 15))
    
    # Contenido
    contenido = tk.Frame(frame, bg=COLOR_BLANCO)
    contenido.pack(fill="both", expand=True, padx=20, pady=(0, 20))
    return contenido

def crear_seccion_erp(parent, titulo):
    """Crea un contenedor con título para agrupar campos, con bordes redondeados simulados."""
    container = tk.Frame(parent, bg=COLOR_BLANCO)
    container.pack(fill="x", pady=8)
    
    lbl = tk.Label(container, text=titulo.upper(), font=("Segoe UI", escalar_fuente(7), "bold"), bg=COLOR_BLANCO, fg="#94a3b8")
    lbl.pack(anchor="w", padx=2, pady=(0, 4))
    
    sub_frame = tk.Frame(container, bg=COLOR_BLANCO, bd=0, highlightthickness=1, highlightbackground="#f1f5f9")
    sub_frame.pack(fill="x")
    
    # Padding interno
    inner = tk.Frame(sub_frame, bg=COLOR_BLANCO, padx=12, pady=12)
    inner.pack(fill="x")
    return inner

def crear_label_input(parent, label_text, row, col=0, width=25, is_combo=False, values=None):
    """Helper para crear label + input con estilo consistente."""
    parent.grid_columnconfigure(col + 1, weight=1)
    tk.Label(parent, text=label_text, bg=COLOR_BLANCO, font=("Segoe UI", escalar_fuente(9)), fg="#334155").grid(row=row, column=col, sticky="w", pady=escalar(5))
    if is_combo:
        ent = ttk.Combobox(parent, values=values or [], state="readonly" if values else "normal", width=width-2)
        ent.grid(row=row, column=col+1, padx=(10, 0), pady=5, sticky="ew")
        return ent
    else:
        # El estilo global manejado en ventana_principal.py se encarga de bordes y foco
        ent = tk.Entry(parent, width=width)
        ent.grid(row=row, column=col+1, padx=(10, 0), pady=5, sticky="ew")
        return ent

# --- PLACEHOLDERS PARA INICIALIZACIÓN ---
# Estos se irán completando en las siguientes tareas

def inicializar_tab_registro(self):
    from database.proveedores import obtener_proveedores
    from database.plan_cuentas import obtener_plan_cuentas
    
    # Contenedor dividido en 2 columnas
    contenedor = tk.Frame(self.tab_registro, bg=COLOR_GRIS)
    contenedor.pack(fill="both", expand=True)

    # === PANEL IZQUIERDO: FORMULARIO (con scroll) ===
    from modulos.utils_globales import crear_frame_scrollable
    col_izq_scroll, col_izq = crear_frame_scrollable(contenedor, bg=COLOR_GRIS)
    col_izq_scroll.pack(side="left", fill="both", expand=True, padx=(0, 10))
    
    tarjeta_form = render_tarjeta_erp(col_izq, "Ingreso de Documento / Gasto")
    
    # --- Datos del Documento ---
    f_doc = crear_seccion_erp(tarjeta_form, "Datos del Documento")
    
    # Qué operaciones y cuentas aplican depende del tipo de negocio
    # (ver database/negocio.py). Un negocio de servicios no repone inventario.
    from database.negocio import (
        maneja_inventario, tipos_de_operacion_disponibles, cuentas_aplicables
    )
    _con_inventario = maneja_inventario()

    tipos_operacion = tipos_de_operacion_disponibles()
    self.cmb_tipo_op = crear_label_input(f_doc, "Tipo Operación:", 0, is_combo=True,
                                        values=tipos_operacion)
    self.cmb_tipo_op.set(tipos_operacion[0])
    
    self.cmb_tipo_doc = crear_label_input(f_doc, "Tipo Documento:", 1, is_combo=True, 
                                        values=["factura", "factura_electronica", "boleta", "honorarios", "otro"])
    self.cmb_tipo_doc.set("factura")
    
    self.ent_num_doc = crear_label_input(f_doc, "N° Documento:", 2)
    
    self.ent_fecha_doc = crear_label_input(f_doc, "Fecha Documento:", 3, width=15)
    hoy = date.today()
    self.ent_fecha_doc.insert(0, hoy.strftime("%d-%m-%Y"))
    tk.Label(f_doc, text="(DD-MM-AAAA)", bg=COLOR_BLANCO, font=("Segoe UI", escalar_fuente(8)), fg="#94a3b8").grid(row=3, column=2, padx=5, sticky="w")

    self.provs = obtener_proveedores()
    self.cmb_prov = crear_label_input(f_doc, "Proveedor:", 4, is_combo=True, values=[p['nombre'] for p in self.provs])
    
    self.cuentas = cuentas_aplicables(obtener_plan_cuentas())

    self.cmb_cuenta = crear_label_input(f_doc, "Cuenta Contable:", 5, is_combo=True,
                                        values=[f"{c['codigo']} - {c['nombre']}" for c in self.cuentas])

    # Preseleccionar una cuenta que exista de verdad en la lista mostrada:
    # dejar fija "Mercaderías" hacía que en modo servicios el combo arrancara
    # con un valor que ya no estaba entre las opciones.
    _preferida = "1.1 - Mercaderías" if _con_inventario else None
    _opciones = [f"{c['codigo']} - {c['nombre']}" for c in self.cuentas]
    if _preferida in _opciones:
        self.cmb_cuenta.set(_preferida)
    elif _opciones:
        self.cmb_cuenta.set(_opciones[0])
    
    self.ent_descripcion = crear_label_input(f_doc, "Descripción (Opcional):", 6)

    # --- Montos ---
    f_pago = crear_seccion_erp(tarjeta_form, "Pago y Montos")
    
    self.ent_total = crear_label_input(f_pago, "Monto Total:", 0, width=20)
    self.ent_total.config(font=("Segoe UI", escalar_fuente(12), "bold"), fg="#166534")
    self.ent_total.bind("<KeyRelease>", formatear_con_miles, add="+")
    
    self.cmb_condicion = crear_label_input(f_pago, "Condición Pago:", 1, is_combo=True, values=["pagado", "pendiente"])
    self.cmb_condicion.set("pagado")
    
    # Botón Principal
    btn_registrar = tk.Button(
        tarjeta_form, text="REGISTRAR DOCUMENTO", bg=COLOR_PRIMARIO, fg=COLOR_BLANCO,
        relief="flat", font=("Segoe UI", escalar_fuente(11), "bold"), cursor="hand2",
        command=lambda: procesar_registro_compra(self)
    )
    btn_registrar.pack(fill="x", pady=(10, 0), ipady=10)
    
    # === PANEL DERECHO: RECIENTES ===
    col_der = tk.Frame(contenedor, bg=COLOR_GRIS)
    col_der.pack(side="right", fill="both", expand=True)
    
    tarjeta_recientes = render_tarjeta_erp(col_der, "Últimos Movimientos")
    
    columnas = ("fecha", "tipo", "doc", "total", "estado")
    self.tree_recientes = ttk.Treeview(tarjeta_recientes, columns=columnas, show="headings", style="ERP.Treeview")
    
    self.tree_recientes.heading("fecha", text="Fecha")
    self.tree_recientes.heading("tipo", text="Tipo")
    self.tree_recientes.heading("doc", text="N° Doc")
    self.tree_recientes.heading("total", text="Total")
    self.tree_recientes.heading("estado", text="Estado")
    
    self.tree_recientes.column("fecha", width=escalar(90), anchor="center")
    self.tree_recientes.column("tipo", width=escalar(120), anchor="w")
    self.tree_recientes.column("doc", width=escalar(100), anchor="w")
    self.tree_recientes.column("total", width=escalar(100), anchor="e")
    self.tree_recientes.column("estado", width=escalar(80), anchor="center")
    self.tree_recientes.pack(fill="both", expand=True)

    self.btn_anular_mov = tk.Button(
        tarjeta_recientes, text="🚫 ANULAR MOVIMIENTO SELECCIONADO", bg="#fef2f2", fg=COLOR_PELIGRO,
        relief="flat", font=("Segoe UI", escalar_fuente(8), "bold"), cursor="hand2", state="disabled", height=2,
        command=lambda: procesar_anular_compra(self)
    )
    self.btn_anular_mov.pack(fill="x", pady=(10, 0))
    
    self.tree_recientes.bind("<<TreeviewSelect>>", lambda e: on_select_reciente(self))
    self.tree_recientes.bind("<Double-1>", lambda e: abrir_modal_detalles_documento(self))
    
    actualizar_recientes_compras(self)

def on_select_reciente(self):
    seleccion = self.tree_recientes.selection()
    if seleccion:
        item = self.tree_recientes.item(seleccion[0])
        estado = item['values'][4]
        if 'anulado' in estado.lower():
            self.btn_anular_mov.config(state="disabled")
        else:
            self.btn_anular_mov.config(state="normal")
    else:
        self.btn_anular_mov.config(state="disabled")

def abrir_modal_detalles_documento(self):
    """Abre un modal con todos los detalles del documento seleccionado."""
    try:
        seleccion = self.tree_recientes.selection()
        if not seleccion:
            return
        
        compra_id = int(seleccion[0])
        from database.connection import session_db
        from database.proveedores import obtener_proveedores
        from database.plan_cuentas import obtener_plan_cuentas
        
        with session_db(dict_rows=True) as conn:
            res = conn.execute(
                """SELECT id, numero_documento, tipo_documento, fecha, proveedor_id, 
                          tipo_operacion, subtotal, impuesto, descuento, total, 
                          estado_pago, estado, observacion, saldo_pendiente, cuenta_contable_id,
                          usuario_id
                   FROM compras WHERE id = ?""", 
                (compra_id,)
            ).fetchone()
        
        if not res:
            messagebox.showerror("Error", "No se encontró el documento")
            return
        
        # Obtener datos relacionados
        proveedores = {p['id']: p['nombre'] for p in obtener_proveedores()}
        cuentas = {c['id']: f"{c['codigo']} - {c['nombre']}" for c in obtener_plan_cuentas()}
        
        proveedor_nombre = proveedores.get(res['proveedor_id'], "N/A") if res['proveedor_id'] else "N/A"
        cuenta_nombre = cuentas.get(res['cuenta_contable_id'], "N/A") if res['cuenta_contable_id'] else "N/A"
        
        # Crear ventana modal
        modal = tk.Toplevel(self.root)
        modal.title(f"Detalle Documento - {res['numero_documento']}")
        modal.resizable(False, False)
        modal.grab_set()
        aplicar_barra_windows_azul(modal)
        centrar_ventana_mejorado(modal, escalar(600), escalar(720), relativo_a=self.root)
        
        # Header
        header = tk.Frame(modal, bg=COLOR_PRIMARIO, height=escalar(50))
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(
            header, text=f"📄 {res['numero_documento']}", 
            font=("Segoe UI", escalar_fuente(14), "bold"), fg=COLOR_BLANCO, bg=COLOR_PRIMARIO
        ).pack(side="left", padx=20, pady=15)
        
        # Contenido principal con scroll adaptativo y soporte de rueda de ratón
        scroll_body = preparar_modal_scrollable(modal, bg=COLOR_BLANCO)
        scrollable_frame = tk.Frame(scroll_body, bg=COLOR_BLANCO, padx=15, pady=15)
        scrollable_frame.pack(fill="both", expand=True)
        
        # Función auxiliar para mostrar pares clave-valor
        def agregar_fila(frame, label, valor, bold=False):
            fila = tk.Frame(frame, bg=COLOR_BLANCO)
            fila.pack(fill="x", pady=6)
            
            font_label = ("Segoe UI", escalar_fuente(9), "bold") if bold else ("Segoe UI", escalar_fuente(9))
            font_valor = ("Segoe UI", escalar_fuente(10), "bold") if bold else ("Segoe UI", escalar_fuente(10))
            
            tk.Label(fila, text=label, bg=COLOR_BLANCO, font=font_label, fg="#64748b", width=22, anchor="w").pack(side="left", anchor="w")
            tk.Label(fila, text=str(valor), bg=COLOR_BLANCO, font=font_valor, fg="#1e293b", wraplength=280, justify="left").pack(side="left", fill="both", expand=True, padx=(5, 0))
        
        # Sección: Información del Documento
        seccion_titulo = tk.Label(scrollable_frame, text="INFORMACIÓN DEL DOCUMENTO", bg=COLOR_BLANCO, font=("Segoe UI", escalar_fuente(9), "bold"), fg="#94a3b8")
        seccion_titulo.pack(anchor="w", pady=(0, 8))
        
        agregar_fila(scrollable_frame, "Tipo de Operación:", res['tipo_operacion'].replace('_', ' ').title(), bold=True)
        agregar_fila(scrollable_frame, "Tipo de Documento:", res['tipo_documento'].replace('_', ' ').title())
        agregar_fila(scrollable_frame, "N° Documento:", res['numero_documento'])
        agregar_fila(scrollable_frame, "Fecha:", _fmt_fecha(res['fecha']))
        agregar_fila(scrollable_frame, "Proveedor:", proveedor_nombre)
        
        # Sección: Información Contable
        tk.Frame(scrollable_frame, height=1, bg="#f1f5f9").pack(fill="x", pady=10)
        seccion_titulo = tk.Label(scrollable_frame, text="INFORMACIÓN CONTABLE", bg=COLOR_BLANCO, font=("Segoe UI", escalar_fuente(9), "bold"), fg="#94a3b8")
        seccion_titulo.pack(anchor="w", pady=(0, 8))
        
        agregar_fila(scrollable_frame, "Cuenta Contable:", cuenta_nombre)
        agregar_fila(scrollable_frame, "Subtotal:", f"$ {res['subtotal']:,.0f}")
        agregar_fila(scrollable_frame, "Descuento:", f"$ {res['descuento']:,.0f}")
        agregar_fila(scrollable_frame, "Impuesto (IVA):", f"$ {res['impuesto']:,.0f}")
        agregar_fila(scrollable_frame, "Total:", f"$ {res['total']:,.0f}", bold=True)
        
        # Sección: Estado de Pago
        tk.Frame(scrollable_frame, height=1, bg="#f1f5f9").pack(fill="x", pady=10)
        seccion_titulo = tk.Label(scrollable_frame, text="ESTADO DE PAGO", bg=COLOR_BLANCO, font=("Segoe UI", escalar_fuente(9), "bold"), fg="#94a3b8")
        seccion_titulo.pack(anchor="w", pady=(0, 8))
        
        agregar_fila(scrollable_frame, "Condición Pago:", res['estado_pago'].capitalize())
        agregar_fila(scrollable_frame, "Saldo Pendiente:", f"$ {res['saldo_pendiente']:,.0f}")
        
        # Estado del Documento
        estado_display = res['estado'].upper() if res['estado'] != 'registrada' else 'REGISTRADO'
        agregar_fila(scrollable_frame, "Estado:", estado_display)
        
        # Sección: Descripción/Observación
        if res['observacion'] and res['observacion'].strip():
            tk.Frame(scrollable_frame, height=1, bg="#f1f5f9").pack(fill="x", pady=10)
            seccion_titulo = tk.Label(scrollable_frame, text="DESCRIPCIÓN / OBSERVACIONES", bg=COLOR_BLANCO, font=("Segoe UI", escalar_fuente(9), "bold"), fg="#94a3b8")
            seccion_titulo.pack(anchor="w", pady=(0, 8))
            
            # Frame para la descripción con fondo gris claro
            desc_frame = tk.Frame(scrollable_frame, bg="#f8fafc", bd=1, highlightthickness=1, highlightbackground="#e2e8f0")
            desc_frame.pack(fill="x", pady=5)
            
            desc_label = tk.Label(
                desc_frame, text=res['observacion'], bg="#f8fafc", font=("Segoe UI", escalar_fuente(9)),
                fg="#334155", wraplength=480, justify="left", padx=10, pady=10
            )
            desc_label.pack(anchor="w", fill="both", expand=True)
        
        # Footer con botón cerrar
        footer = tk.Frame(modal, bg=COLOR_BLANCO, height=escalar(60))
        footer.pack(fill="x", padx=15, pady=15)
        footer.pack_propagate(False)
        
        btn_cerrar = tk.Button(
            footer, text="CERRAR", bg=COLOR_PRIMARIO, fg=COLOR_BLANCO,
            relief="flat", font=("Segoe UI", escalar_fuente(10), "bold"), cursor="hand2",
            command=modal.destroy
        )
        btn_cerrar.pack(fill="x", ipady=8)
        
        # Permitir cerrar con Escape
        modal.bind("<Escape>", lambda e: modal.destroy())
    
    except Exception as e:
        get_logger("compras").exception("Falló al abrir detalle de compra")
        messagebox.showerror("Error", f"Error al abrir detalles: {str(e)}")

def procesar_anular_compra(self):
    from database.compras import anular_compra
    seleccion = self.tree_recientes.selection()
    if not seleccion: return
    
    if messagebox.askyesno("Confirmar", "¿Está seguro que desea anular este documento?\nEsta acción revertirá stock y movimientos de caja."):
        compra_id = int(seleccion[0])
        if anular_compra(compra_id, usuario_id=Sesion.get_usuario_id()):
            messagebox.showinfo("Éxito", "Documento anulado correctamente")
            actualizar_recientes_compras(self)
            # Actualizar deudas por si acaso
            if hasattr(self, 'tree_deudas'): actualizar_tabla_deudas(self)
        else:
            messagebox.showerror("Error", "No se pudo anular el documento")

def actualizar_recientes_compras(self):
    from database.connection import session_db
    self.tree_recientes.delete(*self.tree_recientes.get_children())
    with session_db(dict_rows=True) as conn:
        res = conn.execute("SELECT id, fecha, tipo_operacion, numero_documento, total, estado_pago, estado FROM compras ORDER BY id DESC LIMIT 15").fetchall()
        for r in res:
            tag = "anulada" if r['estado'] == 'anulada' else ""
            display_estado = r['estado_pago'] if r['estado'] != 'anulada' else 'ANULADO'
            self.tree_recientes.insert("", "end", iid=str(r['id']), values=(_fmt_fecha(r['fecha']), r['tipo_operacion'], r['numero_documento'], f"$ {r['total']:,.0f}", display_estado), tags=(tag,))
    
    self.tree_recientes.tag_configure("anulada", foreground="gray")

def refrescar_combos_maestros(self):
    """Actualiza los desplegables de proveedores y cuentas contables con datos frescos."""
    from database.proveedores import obtener_proveedores
    from database.plan_cuentas import obtener_plan_cuentas
    
    self.provs = obtener_proveedores()
    self.cuentas = obtener_plan_cuentas()
    
    if hasattr(self, 'cmb_prov'):
        self.cmb_prov['values'] = [p['nombre'] for p in self.provs]
    
    if hasattr(self, 'cmb_cuenta'):
        self.cmb_cuenta['values'] = [f"{c['codigo']} - {c['nombre']}" for c in self.cuentas]

def procesar_registro_compra(self):
    from database.compras import registrar_compra_erp
    from datetime import datetime
    
    tipo_op = self.cmb_tipo_op.get()
    tipo_doc = getattr(self, "cmb_tipo_doc", None)
    tipo_doc_val = tipo_doc.get() if tipo_doc else "factura"
    num_doc = self.ent_num_doc.get()
    fecha_raw = self.ent_fecha_doc.get().strip()
    prov_nom = self.cmb_prov.get()
    cuenta_raw = self.cmb_cuenta.get()
    monto_str = self.ent_total.get()
    condicion = self.cmb_condicion.get()
    
    descripcion = getattr(self, "ent_descripcion", None)
    desc_val = descripcion.get().strip() if descripcion else ""
    
    if not num_doc or not monto_str:
        messagebox.showwarning("Faltan Datos", "Por favor ingrese N° Documento y Monto Total")
        return

    # Parsear fecha DD-MM-AAAA -> AAAA-MM-DD
    fecha_iso = None
    try:
        dt = datetime.strptime(fecha_raw, "%d-%m-%Y")
        fecha_iso = dt.strftime("%Y-%m-%d")
    except Exception:
        messagebox.showwarning("Fecha inválida", "La fecha debe estar en formato DD-MM-AAAA")
        return
        
    try:
        # Limpiar puntos antes de convertir
        monto = float(limpiar_formato_numerico(monto_str))
        if monto <= 0:
            messagebox.showwarning("Monto inválido", "El monto total debe ser mayor a cero")
            return
        # Buscar ID de cuenta (validado: antes un texto no coincidente
        # lanzaba IndexError con un mensaje críptico)
        coincidencias = [c['id'] for c in self.cuentas if f"{c['codigo']} - {c['nombre']}" == cuenta_raw]
        if not coincidencias:
            messagebox.showwarning("Cuenta contable", "Seleccione una cuenta contable válida de la lista")
            return
        cuenta_id = coincidencias[0]
        # Buscar ID de proveedor (opcional)
        prov_id = None
        if prov_nom:
            for p in self.provs:
                if p['nombre'] == prov_nom:
                    prov_id = p['id']
                    break

        # Calcular IVA con el porcentaje configurado (antes 19% fijo)
        if tipo_doc_val in ["factura", "factura_electronica"] and tipo_op != "sueldos":
            try:
                from database.finanzas_utils import obtener_config_finanzas
                iva_pct = obtener_config_finanzas().get("iva_porcentaje", 19.0)
            except Exception:
                iva_pct = 19.0
            subtotal = round(monto / (1 + iva_pct / 100))
            impuesto = monto - subtotal
        else:
            subtotal = monto
            impuesto = 0

        # Registrar
        registrar_compra_erp(
            tipo_operacion=tipo_op,
            proveedor_id=prov_id,
            numero_documento=num_doc,
            tipo_documento=tipo_doc_val,
            total=monto,
            subtotal=subtotal,
            impuesto=impuesto,
            cuenta_contable_id=cuenta_id,
            estado_pago=condicion,
            usuario_id=Sesion.get_usuario_id(),
            fecha=fecha_iso,
            observacion=desc_val
        )
        
        messagebox.showinfo("Éxito", "Documento registrado correctamente")
        # Limpiar formulario
        self.ent_num_doc.delete(0, tk.END)
        self.ent_total.delete(0, tk.END)
        if descripcion:
            descripcion.delete(0, tk.END)
        actualizar_recientes_compras(self)
        
    except ValueError:
        messagebox.showerror("Error", "El monto debe ser un número válido")
    except Exception as e:
        get_logger("compras").exception("Falló el registro de compra")
        messagebox.showerror("Error", f"No se pudo registrar: {e}")

def inicializar_tab_cuentas_pagar(self):
    tarjeta = render_tarjeta_erp(self.tab_cuentas_pagar, "Listado de Cuentas por Pagar")
    
    # Contenedor Tabla
    frame_lista = tk.Frame(tarjeta, bg=COLOR_BLANCO)
    frame_lista.pack(fill="both", expand=True)
    
    columnas = ("num", "prov", "fecha", "antiguedad", "total", "saldo", "estado")
    self.tree_deudas = ttk.Treeview(frame_lista, columns=columnas, show="headings", style="ERP.Treeview")
    
    self.tree_deudas.heading("num", text="Documento")
    self.tree_deudas.heading("prov", text="Proveedor")
    self.tree_deudas.heading("fecha", text="Fecha")
    self.tree_deudas.heading("antiguedad", text="Antig.")
    self.tree_deudas.heading("total", text="Total")
    self.tree_deudas.heading("saldo", text="Saldo Pendiente")
    self.tree_deudas.heading("estado", text="Estado")
    
    self.tree_deudas.column("num", width=escalar(120))
    self.tree_deudas.column("fecha", width=escalar(100), anchor="center")
    self.tree_deudas.column("antiguedad", width=escalar(65), anchor="center")
    self.tree_deudas.column("total", width=escalar(110), anchor="e")
    self.tree_deudas.column("saldo", width=escalar(110), anchor="e")
    self.tree_deudas.column("estado", width=escalar(90), anchor="center")
    
    sb = ttk.Scrollbar(frame_lista, orient="vertical", command=self.tree_deudas.yview)
    self.tree_deudas.configure(yscrollcommand=sb.set)
    
    self.tree_deudas.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")
    
    # Barra de acciones (dentro de la misma tarjeta o debajo)
    f_acciones_c = crear_seccion_erp(tarjeta, "Acciones de Pago")
    
    tk.Label(f_acciones_c, text="Monto a Pagar:", bg=COLOR_BLANCO, font=("Segoe UI", escalar_fuente(10))).pack(side="left", padx=5)
    self.ent_monto_pago = tk.Entry(f_acciones_c, width=15, font=("Segoe UI", escalar_fuente(11), "bold"))
    self.ent_monto_pago.pack(side="left", padx=5)
    self.ent_monto_pago.bind("<KeyRelease>", formatear_con_miles, add="+")
    
    tk.Button(
        f_acciones_c, text="REGISTRAR PAGO / ABONO", bg=COLOR_SECUNDARIO, fg=COLOR_BLANCO,
        relief="flat", font=("Segoe UI", escalar_fuente(9), "bold"), cursor="hand2",
        command=lambda: procesar_pago_deuda(self)
    ).pack(side="left", padx=20, ipadx=10, ipady=3)
    
    tk.Button(
        f_acciones_c, text="📊 Generar Reporte CSV", bg="#f1f5f9", fg="#475569",
        relief="flat", font=("Segoe UI", escalar_fuente(9), "bold"), cursor="hand2",
        command=lambda: exportar_reporte_cuentas_pagar(self)
    ).pack(side="right", padx=10, pady=5)
    
    actualizar_tabla_deudas(self)

def actualizar_tabla_deudas(self):
    from database.compras import obtener_compras_pendientes
    self.tree_deudas.delete(*self.tree_deudas.get_children())
    self.deudas_actuales = obtener_compras_pendientes()
    hoy = date.today()
    for d in self.deudas_actuales:
        fecha_raw = str(d.get('fecha', ''))[:10]
        fecha_disp = _fmt_fecha(fecha_raw)
        # Calcular antigüedad en días
        try:
            fecha_dt = datetime.strptime(fecha_raw, "%Y-%m-%d").date()
            dias = (hoy - fecha_dt).days
            antiguedad = f"{dias}d"
        except Exception:
            dias = 0
            antiguedad = "-"
        
        # Colorear según antigüedad
        if dias > 30:
            tag_color = "vencida"
        elif dias > 15:
            tag_color = "proxima"
        else:
            tag_color = ""
        
        self.tree_deudas.insert(
            "", "end", iid=str(d['id']),
            values=(
                d['numero_documento'], d['nombre_proveedor'] or "N/A", 
                fecha_disp, antiguedad,
                f"$ {d['total']:,.0f}", 
                f"$ {d['saldo_pendiente']:,.0f}", d['estado_pago'].upper()
            ),
            tags=(tag_color,)
        )
    self.tree_deudas.tag_configure("vencida", foreground="#dc3545", background="#fff5f5")
    self.tree_deudas.tag_configure("proxima", foreground="#e67e22", background="#fff8f0")

def procesar_pago_deuda(self):
    from database.compras import registrar_pago_documento
    seleccion = self.tree_deudas.selection()
    if not seleccion:
        messagebox.showwarning("Selección", "Por favor seleccione un documento de la lista")
        return
        
    compra_id = int(seleccion[0])
    monto_str = self.ent_monto_pago.get()
    
    if not monto_str:
        messagebox.showwarning("Monto", "Ingrese el monto a pagar")
        return
        
    try:
        monto = float(limpiar_formato_numerico(monto_str))
        registrar_pago_documento(compra_id, monto, usuario_id=Sesion.get_usuario_id())
        messagebox.showinfo("Éxito", "Pago registrado correctamente")
        self.ent_monto_pago.delete(0, tk.END)
        actualizar_tabla_deudas(self)
        # También actualizar recientes si está visible
        actualizar_recientes_compras(self)
    except Exception as e:
        get_logger("compras").exception("Falló el registro de pago")
        messagebox.showerror("Error", f"No se pudo registrar el pago: {e}")

def exportar_reporte_cuentas_pagar(self):
    from tkinter import filedialog
    import csv
    
    if not hasattr(self, 'deudas_actuales') or not self.deudas_actuales:
        messagebox.showwarning("Sin datos", "No hay cuentas por pagar para exportar.")
        return
        
    filepath = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv")],
        title="Exportar Cuentas por Pagar",
        initialfile=f"cuentas_por_pagar_{date.today().strftime('%Y%m%d')}.csv"
    )
    if not filepath:
        return
        
    try:
        with open(filepath, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")  # ";" como el resto de reportes (Excel es-CL)
            writer.writerow(["Documento", "Proveedor", "Fecha", "Total", "Saldo Pendiente", "Estado"])
            for d in self.deudas_actuales:
                writer.writerow([
                    d.get("numero_documento"),
                    d.get("nombre_proveedor") or "N/A",
                    _fmt_fecha(d.get("fecha")),
                    d.get("total"),
                    d.get("saldo_pendiente"),
                    d.get("estado_pago").upper()
                ])
        messagebox.showinfo("Éxito", f"Reporte exportado correctamente:\n{filepath}")
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo exportar: {e}")

def inicializar_tab_empleados(self):
    # Contenedor dividido: Izquierda para Listado y liquidaciones, Derecha para Ficha
    contenedor = tk.Frame(self.tab_empleados, bg=COLOR_GRIS)
    contenedor.pack(fill="both", expand=True)

    col_izq = tk.Frame(contenedor, bg=COLOR_GRIS)
    col_izq.pack(side="left", fill="both", expand=True, padx=(0, 10))
    
    col_der = tk.Frame(contenedor, bg=COLOR_GRIS, width=max(300, escalar(350)))
    col_der.pack(side="right", fill="both", expand=False)
    col_der.pack_propagate(False)
    
    # --- Tarjeta 1: Listado de Empleados ---
    tarjeta_lista = render_tarjeta_erp(col_izq, "Personal Registrado")
    
    columnas = ("rut", "nombre", "cargo", "sueldo")
    self.tree_empleados = ttk.Treeview(tarjeta_lista, columns=columnas, show="headings", style="ERP.Treeview")
    
    self.tree_empleados.heading("rut", text="RUT / ID")
    self.tree_empleados.heading("nombre", text="Nombre")
    self.tree_empleados.heading("cargo", text="Cargo")
    self.tree_empleados.heading("sueldo", text="Sueldo Base")
    
    self.tree_empleados.column("rut", width=escalar(110), anchor="center")
    self.tree_empleados.column("nombre", width=escalar(200), anchor="w")
    self.tree_empleados.column("cargo", width=escalar(110), anchor="center")
    self.tree_empleados.column("sueldo", width=escalar(110), anchor="e")
    
    self.tree_empleados.pack(fill="both", expand=True)
    self.tree_empleados.configure(height=5)
    
    # Botones debajo de la lista
    f_btns_emp = tk.Frame(tarjeta_lista, bg=COLOR_BLANCO)
    f_btns_emp.pack(fill="x", pady=(10, 20))
    
    self.btn_edit_emp = tk.Button(f_btns_emp, text="📝 Editar", bg=COLOR_SECUNDARIO, fg=COLOR_BLANCO, relief="flat", font=("Segoe UI", escalar_fuente(9), "bold"), cursor="hand2", state="disabled", command=lambda: cargar_empleado_en_form(self))
    self.btn_edit_emp.pack(side="left", padx=5)
    
    self.btn_del_emp = tk.Button(f_btns_emp, text="🗑️ Eliminar", bg="#fee2e2", fg=COLOR_PELIGRO, relief="flat", font=("Segoe UI", escalar_fuente(9), "bold"), cursor="hand2", state="disabled", command=lambda: procesar_eliminar_empleado(self))
    self.btn_del_emp.pack(side="left", padx=5)

    self.btn_pagar_sueldo = tk.Button(f_btns_emp, text="💰 Pagar Sueldo", bg="#dcfce7", fg="#166534", relief="flat", font=("Segoe UI", escalar_fuente(9), "bold"), cursor="hand2", state="disabled", command=lambda: abrir_form_liquidacion(self))
    self.btn_pagar_sueldo.pack(side="right", padx=5)
    
    tk.Button(f_btns_emp, text="📊 Reporte de Sueldos", bg="#f1f5f9", fg="#475569", relief="flat", font=("Segoe UI", escalar_fuente(9), "bold"), cursor="hand2", command=lambda: exportar_reporte_sueldos(self)).pack(side="right", padx=5)

    # --- Tarjeta 2: Historial Liquidaciones ---
    tarjeta_liq = render_tarjeta_erp(col_izq, "Historial de Liquidaciones")
    
    cols_liq = ("periodo", "empleado", "cargo", "sueldo_base", "bonos", "descuentos", "total_liquido", "estado")
    self.tree_liquidaciones = ttk.Treeview(tarjeta_liq, columns=cols_liq, show="headings", style="ERP.Treeview")
    self.tree_liquidaciones.heading("periodo", text="Período")
    self.tree_liquidaciones.heading("empleado", text="Empleado")
    self.tree_liquidaciones.heading("cargo", text="Cargo")
    self.tree_liquidaciones.heading("sueldo_base", text="Base")
    self.tree_liquidaciones.heading("bonos", text="Bonos")
    self.tree_liquidaciones.heading("descuentos", text="Dctos")
    self.tree_liquidaciones.heading("total_liquido", text="Líquido")
    self.tree_liquidaciones.heading("estado", text="Estado")

    self.tree_liquidaciones.column("periodo", width=escalar(75), anchor="center")
    self.tree_liquidaciones.column("empleado", width=escalar(140), anchor="w")
    self.tree_liquidaciones.column("cargo", width=escalar(90), anchor="center")
    self.tree_liquidaciones.column("sueldo_base", width=escalar(80), anchor="e")
    self.tree_liquidaciones.column("bonos", width=escalar(70), anchor="e")
    self.tree_liquidaciones.column("descuentos", width=escalar(70), anchor="e")
    self.tree_liquidaciones.column("total_liquido", width=escalar(90), anchor="e")
    self.tree_liquidaciones.column("estado", width=escalar(70), anchor="center")
    self.tree_liquidaciones.pack(fill="both", expand=True)

    self.btn_anular_liq = tk.Button(tarjeta_liq, text="🚫 Anular Liquidación", bg="#f8fafc", fg="#64748b", relief="flat", font=("Segoe UI", escalar_fuente(8), "bold"), cursor="hand2", state="disabled", command=lambda: procesar_anular_liquidacion(self))
    self.btn_anular_liq.pack(anchor="e", pady=(10, 0))

    # --- Tarjeta 3 (DERECHA): Ficha de Empleado ---
    tarjeta_ficha = render_tarjeta_erp(col_der, "Ficha de Empleado")
    
    f_inputs = tk.Frame(tarjeta_ficha, bg=COLOR_BLANCO)
    f_inputs.pack(fill="both", expand=True)
    
    self.ent_rut_emp = crear_label_input(f_inputs, "RUT / Identificador:", 0)
    self.ent_rut_emp.bind("<KeyRelease>", formatear_rut)
    
    self.ent_nom_emp = crear_label_input(f_inputs, "Nombre Completo:", 1)
    
    self.ent_cargo_emp = crear_label_input(f_inputs, "Cargo / Rol:", 2)
    
    self.ent_sueldo_emp = crear_label_input(f_inputs, "Sueldo Base ($):", 3)
    self.ent_sueldo_emp.config(font=("Segoe UI", escalar_fuente(11), "bold"), fg=COLOR_PRIMARIO)
    self.ent_sueldo_emp.bind("<KeyRelease>", formatear_con_miles, add="+")
    
    # Re-grid para que se vean verticales (por defecto el helper usa grid horizontal)
    # Ajustamos el layout de la ficha para que sea vertical mejor
    for i, w in enumerate(f_inputs.winfo_children()):
        if isinstance(w, tk.Label):
            w.grid(row=i*2, column=0, sticky="w", pady=(10, 0))
        elif isinstance(w, (tk.Entry, ttk.Combobox)):
            w.grid(row=i*2+1, column=0, sticky="ew", pady=(0, 10))
            w.grid_configure(padx=0)
    
    f_inputs.columnconfigure(0, weight=1)
    
    self.btn_guardar_emp = tk.Button(tarjeta_ficha, text="GUARDAR EMPLEADO", bg=COLOR_PRIMARIO, fg=COLOR_BLANCO, relief="flat", font=("Segoe UI", escalar_fuente(10), "bold"), cursor="hand2", height=2, command=lambda: guardar_empleado(self))
    self.btn_guardar_emp.pack(fill="x", pady=(10, 5))

    self.btn_cancelar_emp = tk.Button(tarjeta_ficha, text="Cancelar Edición", bg="#f1f5f9", fg="#64748b", relief="flat", font=("Segoe UI", escalar_fuente(9)), cursor="hand2", command=lambda: limpiar_form_empleado(self))
    self.btn_cancelar_emp.pack(fill="x")

    self.empleado_seleccionado_id = None

    # Eventos
    self.tree_empleados.bind("<<TreeviewSelect>>", lambda e: on_select_empleado(self))
    self.tree_liquidaciones.bind("<<TreeviewSelect>>", lambda e: on_select_liquidacion(self))
    
    actualizar_tabla_empleados(self)
    actualizar_tabla_liquidaciones(self)

def exportar_reporte_sueldos(self):
    from tkinter import filedialog
    from database.empleados import obtener_empleados
    import csv
    
    empleados = obtener_empleados()
    if not empleados:
        messagebox.showwarning("Sin datos", "No hay empleados registrados para exportar.")
        return
        
    filepath = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv")],
        title="Exportar Reporte de Sueldos",
        initialfile=f"reporte_sueldos_{date.today().strftime('%Y%m%d')}.csv"
    )
    if not filepath:
        return
        
    try:
        with open(filepath, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")  # ";" como el resto de reportes (Excel es-CL)
            writer.writerow(["RUT", "Nombre", "Cargo", "Sueldo Base"])
            for e in empleados:
                writer.writerow([
                    e.get("rut"),
                    e.get("nombre"),
                    e.get("cargo"),
                    e.get("sueldo_base")
                ])
        messagebox.showinfo("Éxito", f"Reporte exportado correctamente:\n{filepath}")
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo exportar: {e}")

def on_select_empleado(self):
    seleccion = self.tree_empleados.selection()
    if seleccion:
        self.btn_edit_emp.config(state="normal")
        self.btn_del_emp.config(state="normal")
        self.btn_pagar_sueldo.config(state="normal")
    else:
        self.btn_edit_emp.config(state="disabled")
        self.btn_del_emp.config(state="disabled")
        self.btn_pagar_sueldo.config(state="disabled")

def on_select_liquidacion(self):
    seleccion = self.tree_liquidaciones.selection()
    if seleccion:
        self.btn_anular_liq.config(state="normal")
    else:
        self.btn_anular_liq.config(state="disabled")

def actualizar_tabla_liquidaciones(self):
    from database.liquidaciones import obtener_liquidaciones
    self.tree_liquidaciones.delete(*self.tree_liquidaciones.get_children())
    for liq in obtener_liquidaciones():
        tag = liq.get("estado", "pagado")
        self.tree_liquidaciones.insert(
            "", "end", iid=str(liq["id"]),
            values=(
                liq.get("periodo", ""),
                liq.get("nombre_empleado", ""),
                liq.get("cargo", ""),
                f"$ {liq.get('sueldo_base', 0):,.0f}",
                f"$ {liq.get('bonos', 0):,.0f}",
                f"$ {liq.get('descuentos', 0):,.0f}",
                f"$ {liq.get('total_liquido', 0):,.0f}",
                liq.get("estado", "pagado").upper()
            ),
            tags=(tag,)
        )

def procesar_anular_liquidacion(self):
    from database.liquidaciones import anular_liquidacion
    seleccion = self.tree_liquidaciones.selection()
    if not seleccion:
        return
    if messagebox.askyesno("Confirmar", "¿Anular esta liquidación de sueldo?\nSe revertirá también el gasto asociado en el Estado de Resultados."):
        liq_id = int(seleccion[0])
        item = self.tree_liquidaciones.item(seleccion[0])
        detalle_log = f"Liquidación anulada: {item['values'][1]} - Período: {item['values'][0]}"
        if anular_liquidacion(liq_id):
            registrar_historial(
                accion="Anulación Liquidación",
                tabla="liquidaciones_sueldo",
                referencia_id=liq_id,
                detalles=detalle_log,
                usuario_id=Sesion.get_usuario_id()
            )
            messagebox.showinfo("Éxito", "Liquidación anulada")
            actualizar_tabla_liquidaciones(self)

def abrir_form_liquidacion(self):
    """Abre ventana modal para registrar el pago de sueldo del mes."""
    seleccion = self.tree_empleados.selection()
    if not seleccion:
        return

    from database.empleados import obtener_empleado_por_id
    emp_id = int(seleccion[0])
    emp = obtener_empleado_por_id(emp_id)
    if not emp:
        return

    from database.liquidaciones import crear_liquidacion
    from datetime import date

    top = tk.Toplevel(self.root)
    top.title(f"Liquidación de Sueldo — {emp['nombre']}")
    top.configure(bg=COLOR_BLANCO)
    top.grab_set()
    top.resizable(False, False)
    aplicar_barra_windows_azul(top)
    centrar_ventana_mejorado(top, escalar(480), escalar(380), relativo_a=self.root)

    # Header
    hdr = tk.Frame(top, bg=COLOR_PRIMARIO, height=escalar(55))
    hdr.pack(fill="x")
    hdr.pack_propagate(False)
    tk.Label(hdr, text=f"💰 Liquidación: {emp['nombre']}", font=("Segoe UI", escalar_fuente(12), "bold"),
             fg=COLOR_BLANCO, bg=COLOR_PRIMARIO).pack(side="left", padx=15, pady=12)

    body = preparar_modal_scrollable(top, bg=COLOR_BLANCO)

    cuerpo = tk.Frame(body, bg=COLOR_BLANCO, padx=25, pady=20)
    cuerpo.pack(fill="both", expand=True)

    # Período
    hoy = date.today()
    periodo_defecto = hoy.strftime("%Y-%m")

    tk.Label(cuerpo, text="Período (AAAA-MM):", bg=COLOR_BLANCO, font=("Segoe UI", escalar_fuente(10))).grid(row=0, column=0, sticky="w", pady=5)
    ent_periodo = tk.Entry(cuerpo, width=12, font=("Segoe UI", escalar_fuente(10)))
    ent_periodo.grid(row=0, column=1, padx=10, pady=5, sticky="w")
    ent_periodo.insert(0, periodo_defecto)

    # Sueldo Base (precargado)
    tk.Label(cuerpo, text="Sueldo Base:", bg=COLOR_BLANCO, font=("Segoe UI", escalar_fuente(10))).grid(row=1, column=0, sticky="w", pady=5)
    ent_sueldo = tk.Entry(cuerpo, width=15, font=("Segoe UI", escalar_fuente(10)))
    ent_sueldo.grid(row=1, column=1, padx=10, pady=5, sticky="w")
    ent_sueldo.insert(0, str(int(emp.get("sueldo_base", 0))))
    ent_sueldo.bind("<KeyRelease>", formatear_con_miles, add="+")

    # Bonos
    tk.Label(cuerpo, text="Bonos / Horas Extra:", bg=COLOR_BLANCO, font=("Segoe UI", escalar_fuente(10))).grid(row=2, column=0, sticky="w", pady=5)
    ent_bonos = tk.Entry(cuerpo, width=15, font=("Segoe UI", escalar_fuente(10)))
    ent_bonos.grid(row=2, column=1, padx=10, pady=5, sticky="w")
    ent_bonos.insert(0, "0")
    ent_bonos.bind("<KeyRelease>", formatear_con_miles, add="+")

    # Descuentos
    tk.Label(cuerpo, text="Descuentos (AFP/Salud):", bg=COLOR_BLANCO, font=("Segoe UI", escalar_fuente(10))).grid(row=3, column=0, sticky="w", pady=5)
    ent_desc = tk.Entry(cuerpo, width=15, font=("Segoe UI", escalar_fuente(10)))
    ent_desc.grid(row=3, column=1, padx=10, pady=5, sticky="w")
    ent_desc.insert(0, "0")
    ent_desc.bind("<KeyRelease>", formatear_con_miles, add="+")

    # Vista previa total
    lbl_total_prev = tk.Label(cuerpo, text="Total Líquido: $ 0", bg=COLOR_BLANCO,
                               font=("Segoe UI", escalar_fuente(13), "bold"), fg="#166534")
    lbl_total_prev.grid(row=4, column=0, columnspan=2, pady=(15, 5))

    def recalcular(*_):
        try:
            s = float(limpiar_formato_numerico(ent_sueldo.get() or 0))
            b = float(limpiar_formato_numerico(ent_bonos.get() or 0))
            d = float(limpiar_formato_numerico(ent_desc.get() or 0))
            total = s + b - d
            lbl_total_prev.config(text=f"Total Líquido: $ {total:,.0f}",
                                   fg=("#166534" if total >= 0 else "#dc3545"))
        except Exception:
            lbl_total_prev.config(text="Total Líquido: (revise los montos)", fg="#dc3545")

    for w in (ent_sueldo, ent_bonos, ent_desc):
        w.bind("<KeyRelease>", recalcular)
    recalcular()

    # Observación
    tk.Label(cuerpo, text="Observación:", bg=COLOR_BLANCO, font=("Segoe UI", escalar_fuente(10))).grid(row=5, column=0, sticky="w", pady=5)
    ent_obs = tk.Entry(cuerpo, width=28, font=("Segoe UI", escalar_fuente(10)))
    ent_obs.grid(row=5, column=1, padx=10, pady=5, sticky="ew")

    cuerpo.grid_columnconfigure(1, weight=1)

    def guardar():
        try:
            periodo = ent_periodo.get().strip()
            sueldo = float(limpiar_formato_numerico(ent_sueldo.get() or 0))
            bonos = float(limpiar_formato_numerico(ent_bonos.get() or 0))
            desc = float(limpiar_formato_numerico(ent_desc.get() or 0))
            obs = ent_obs.get().strip()

            # Validar formato Y que el mes sea real (antes "2026-13" pasaba)
            try:
                from datetime import datetime as _dt
                _dt.strptime(periodo, "%Y-%m")
            except ValueError:
                messagebox.showwarning("Error", "Período inválido. Use formato AAAA-MM (ej: 2026-07)", parent=top)
                return

            crear_liquidacion(emp_id, periodo, sueldo, bonos, desc, obs)
            registrar_historial(
                accion="Liquidación Sueldo",
                tabla="liquidaciones_sueldo",
                detalles=f"Liquidación pagada: {emp['nombre']} - Período: {periodo} - Total: $ {(sueldo + bonos - desc):,.0f}",
                usuario_id=Sesion.get_usuario_id()
            )
            messagebox.showinfo("Éxito",
                f"✅ Liquidación registrada\n\nEmpleado: {emp['nombre']}\nPeríodo: {periodo}\nTotal: $ {(sueldo + bonos - desc):,.0f}",
                parent=top)
            top.destroy()
            actualizar_tabla_liquidaciones(self)
        except Exception as exc:
            get_logger("compras").exception("Falló el registro de compra")
            messagebox.showerror("Error", f"No se pudo registrar:\n{exc}", parent=top)

    frame_btns = tk.Frame(body, bg=COLOR_BLANCO)
    frame_btns.pack(fill="x", padx=25, pady=(0, 20))

    tk.Button(frame_btns, text="✅ Confirmar Pago", bg="#28a745", fg=COLOR_BLANCO,
              relief="flat", font=("Segoe UI", escalar_fuente(10), "bold"), cursor="hand2",
              command=guardar).pack(side="left", padx=(0, 10), ipadx=8, ipady=4)

    tk.Button(frame_btns, text="Cancelar", bg="#6c757d", fg=COLOR_BLANCO,
              relief="flat", font=("Segoe UI", escalar_fuente(10)), cursor="hand2",
              command=top.destroy).pack(side="left", ipadx=8, ipady=4)



def cargar_empleado_en_form(self):
    seleccion = self.tree_empleados.selection()
    if not seleccion: return
    
    item = self.tree_empleados.item(seleccion[0])
    valores = item['values']
    self.empleado_seleccionado_id = str(seleccion[0]) # Usaremos el IID que suele ser el ID en mis tablas
    
    self.ent_rut_emp.delete(0, tk.END)
    self.ent_rut_emp.insert(0, valores[0])
    self.ent_nom_emp.delete(0, tk.END)
    self.ent_nom_emp.insert(0, valores[1])
    self.ent_cargo_emp.delete(0, tk.END)
    self.ent_cargo_emp.insert(0, valores[2])
    self.ent_sueldo_emp.delete(0, tk.END)
    # Limpiar el formato de moneda si es necesario ($ 1,234)
    sueldo_raw = str(valores[3]).replace("$", "").replace(",", "").replace(".", "").strip()
    self.ent_sueldo_emp.insert(0, sueldo_raw)
    
    # El botón Cancelar ya está empaquetado con pack(); llamarle .grid()
    # lanzaba TclError (mezcla de geometry managers) en cada edición.
    self.btn_guardar_emp.config(text="ACTUALIZAR DATOS", bg="#f39c12")

def limpiar_form_empleado(self):
    self.empleado_seleccionado_id = None
    self.ent_rut_emp.delete(0, tk.END)
    self.ent_nom_emp.delete(0, tk.END)
    self.ent_cargo_emp.delete(0, tk.END)
    self.ent_sueldo_emp.delete(0, tk.END)
    self.btn_guardar_emp.config(text="GUARDAR CAMBIOS", bg=COLOR_PRIMARIO)

def procesar_eliminar_empleado(self):
    from database.empleados import eliminar_empleado
    seleccion = self.tree_empleados.selection()
    if not seleccion: return
    
    if messagebox.askyesno("Confirmar", "¿Está seguro de que desea eliminar este empleado?"):
        emp_id = int(seleccion[0])
        item = self.tree_empleados.item(seleccion[0])
        nombre_emp = item['values'][1]
        if eliminar_empleado(emp_id):
            registrar_historial(
                accion="Eliminación",
                tabla="empleados",
                referencia_id=emp_id,
                detalles=f"Empleado eliminado: {nombre_emp} (ID: {emp_id})",
                usuario_id=Sesion.get_usuario_id()
            )
            messagebox.showinfo("Éxito", "Empleado eliminado correctamente")
            actualizar_tabla_empleados(self)
        else:
            messagebox.showerror("Error", "No se pudo eliminar el empleado")

def actualizar_tabla_empleados(self):
    from database.empleados import obtener_empleados
    self.tree_empleados.delete(*self.tree_empleados.get_children())
    for e in obtener_empleados():
        sueldo_fmt = f"$ {e['sueldo_base']:,.0f}"
        self.tree_empleados.insert("", "end", iid=str(e['id']), values=(e['rut'], e['nombre'], e['cargo'], sueldo_fmt))

def guardar_empleado(self):
    from database.empleados import crear_empleado, actualizar_empleado
    rut = self.ent_rut_emp.get()
    nom = self.ent_nom_emp.get()
    cargo = self.ent_cargo_emp.get()
    sueldo_str = self.ent_sueldo_emp.get()
    
    if not rut or not nom or not sueldo_str:
        messagebox.showwarning("Error", "RUT, Nombre y Sueldo son obligatorios")
        return
    try:
        sueldo = float(limpiar_formato_numerico(sueldo_str))
        if self.empleado_seleccionado_id:
            # Modo Edición
            actualizar_empleado(int(self.empleado_seleccionado_id), rut=rut, nombre=nom, cargo=cargo, sueldo_base=sueldo)
            registrar_historial(
                accion="Modificación",
                tabla="empleados",
                referencia_id=int(self.empleado_seleccionado_id),
                detalles=f"Empleado actualizado: {nom} (RUT: {rut})",
                usuario_id=Sesion.get_usuario_id()
            )
            messagebox.showinfo("Éxito", "Empleado actualizado correctamente")
        else:
            # Modo Creación
            new_id = crear_empleado(rut, nom, cargo, sueldo)
            registrar_historial(
                accion="Creación",
                tabla="empleados",
                referencia_id=new_id,
                detalles=f"Nuevo empleado registrado: {nom} (RUT: {rut})",
                usuario_id=Sesion.get_usuario_id()
            )
            messagebox.showinfo("Éxito", "Empleado registrado correctamente")
            
        limpiar_form_empleado(self)
        actualizar_tabla_empleados(self)
    except Exception as e:
        get_logger("compras").exception("Falló al guardar (compras)")
        messagebox.showerror("Error", f"No se pudo guardar: {e}")

def inicializar_tab_proveedores(self):
    # Contenedor dividido
    contenedor = tk.Frame(self.tab_proveedores, bg=COLOR_GRIS)
    contenedor.pack(fill="both", expand=True)

    col_izq = tk.Frame(contenedor, bg=COLOR_GRIS)
    col_izq.pack(side="left", fill="both", expand=True, padx=(0, 10))
    
    col_der = tk.Frame(contenedor, bg=COLOR_GRIS, width=max(300, escalar(350)))
    col_der.pack(side="right", fill="both", expand=False)
    col_der.pack_propagate(False)

    # --- Tarjeta 1: Listado ---
    tarjeta_lista = render_tarjeta_erp(col_izq, "Proveedores Registrados")
    
    columnas = ("rut", "nombre", "contacto", "telefono")
    self.tree_proveedores_erp = ttk.Treeview(tarjeta_lista, columns=columnas, show="headings", style="ERP.Treeview")
    
    self.tree_proveedores_erp.heading("rut", text="RUT")
    self.tree_proveedores_erp.heading("nombre", text="Razón Social")
    self.tree_proveedores_erp.heading("contacto", text="Contacto")
    self.tree_proveedores_erp.heading("telefono", text="Teléfono")
    
    self.tree_proveedores_erp.column("rut", width=escalar(110), anchor="center")
    self.tree_proveedores_erp.column("nombre", width=escalar(250), anchor="w")
    self.tree_proveedores_erp.column("contacto", width=escalar(150), anchor="w")
    self.tree_proveedores_erp.column("telefono", width=escalar(110), anchor="center")
    
    self.tree_proveedores_erp.pack(fill="both", expand=True)
    
    # Botones
    f_btns = tk.Frame(tarjeta_lista, bg=COLOR_BLANCO)
    f_btns.pack(fill="x", pady=(15, 0))
    
    self.btn_edit_prov = tk.Button(f_btns, text="📝 Editar", bg=COLOR_SECUNDARIO, fg=COLOR_BLANCO, relief="flat", font=("Segoe UI", escalar_fuente(9), "bold"), cursor="hand2", state="disabled", command=lambda: cargar_proveedor_en_form(self))
    self.btn_edit_prov.pack(side="left", padx=5)
    
    self.btn_del_prov = tk.Button(f_btns, text="🗑️ Eliminar", bg="#fee2e2", fg=COLOR_PELIGRO, relief="flat", font=("Segoe UI", escalar_fuente(9), "bold"), cursor="hand2", state="disabled", command=lambda: procesar_eliminar_proveedor(self))
    self.btn_del_prov.pack(side="left", padx=5)
    
    # --- Tarjeta 2: Formulario ---
    tarjeta_form = render_tarjeta_erp(col_der, "Datos del Proveedor")
    
    f_inputs = tk.Frame(tarjeta_form, bg=COLOR_BLANCO)
    f_inputs.pack(fill="both", expand=True)
    
    self.ent_rut_prov = crear_label_input(f_inputs, "RUT / Identificador:", 0)
    self.ent_rut_prov.bind("<KeyRelease>", formatear_rut)
    
    self.ent_nom_prov = crear_label_input(f_inputs, "Nombre / Razón Social:", 1)
    
    self.ent_cont_prov = crear_label_input(f_inputs, "Persona de Contacto:", 2)
    
    self.ent_tel_prov = crear_label_input(f_inputs, "Teléfono:", 3)
    
    # Ajuste vertical
    for i, w in enumerate(f_inputs.winfo_children()):
        if isinstance(w, tk.Label):
            w.grid(row=i*2, column=0, sticky="w", pady=(10, 0))
        elif isinstance(w, (tk.Entry, ttk.Combobox)):
            w.grid(row=i*2+1, column=0, sticky="ew", pady=(0, 10))
            w.grid_configure(padx=0)
    f_inputs.columnconfigure(0, weight=1)
    
    self.btn_guardar_prov = tk.Button(tarjeta_form, text="GUARDAR PROVEEDOR", bg=COLOR_PRIMARIO, fg=COLOR_BLANCO, relief="flat", font=("Segoe UI", escalar_fuente(10), "bold"), cursor="hand2", height=2, command=lambda: guardar_proveedor_erp(self))
    self.btn_guardar_prov.pack(fill="x", pady=(10, 5))

    self.btn_cancelar_prov = tk.Button(tarjeta_form, text="Cancelar Edición", bg="#f1f5f9", fg="#64748b", relief="flat", font=("Segoe UI", escalar_fuente(9)), cursor="hand2", command=lambda: limpiar_form_proveedor(self))
    self.btn_cancelar_prov.pack(fill="x")
    
    self.proveedor_seleccionado_id = None
    
    # Eventos
    self.tree_proveedores_erp.bind("<<TreeviewSelect>>", lambda e: on_select_proveedor(self))
    
    actualizar_tabla_proveedores_erp(self)

def on_select_proveedor(self):
    seleccion = self.tree_proveedores_erp.selection()
    if seleccion:
        self.btn_edit_prov.config(state="normal")
        self.btn_del_prov.config(state="normal")
    else:
        self.btn_edit_prov.config(state="disabled")
        self.btn_del_prov.config(state="disabled")

def cargar_proveedor_en_form(self):
    seleccion = self.tree_proveedores_erp.selection()
    if not seleccion: return
    
    item = self.tree_proveedores_erp.item(seleccion[0])
    valores = item['values']
    self.proveedor_seleccionado_id = str(seleccion[0])
    
    self.ent_rut_prov.delete(0, tk.END)
    self.ent_rut_prov.insert(0, valores[0])
    self.ent_nom_prov.delete(0, tk.END)
    self.ent_nom_prov.insert(0, valores[1])
    self.ent_cont_prov.delete(0, tk.END)
    self.ent_cont_prov.insert(0, valores[2])
    self.ent_tel_prov.delete(0, tk.END)
    self.ent_tel_prov.insert(0, valores[3])
    
    self.btn_guardar_prov.config(text="ACTUALIZAR PROVEEDOR", bg="#f39c12")

def limpiar_form_proveedor(self):
    self.proveedor_seleccionado_id = None
    self.ent_rut_prov.delete(0, tk.END)
    self.ent_nom_prov.delete(0, tk.END)
    self.ent_cont_prov.delete(0, tk.END)
    self.ent_tel_prov.delete(0, tk.END)
    self.btn_guardar_prov.config(text="GUARDAR PROVEEDOR", bg=COLOR_PRIMARIO)

def procesar_eliminar_proveedor(self):
    from database.proveedores import eliminar_proveedor
    seleccion = self.tree_proveedores_erp.selection()
    if not seleccion: return
    
    if messagebox.askyesno("Confirmar", "¿Está seguro de eliminar este proveedor?"):
        prov_id = int(seleccion[0])
        nombre_prov = self.tree_proveedores_erp.item(seleccion[0])['values'][1]
        if eliminar_proveedor(prov_id):
            registrar_historial(
                accion="Eliminación",
                tabla="proveedores",
                referencia_id=prov_id,
                detalles=f"Proveedor eliminado: {nombre_prov} (ID: {prov_id})",
                usuario_id=Sesion.get_usuario_id()
            )
            messagebox.showinfo("Éxito", "Proveedor eliminado")
            actualizar_tabla_proveedores_erp(self)
        else:
            messagebox.showerror("Error", "No se pudo eliminar")

def actualizar_tabla_proveedores_erp(self):
    from database.proveedores import obtener_proveedores
    self.tree_proveedores_erp.delete(*self.tree_proveedores_erp.get_children())
    for p in obtener_proveedores():
        self.tree_proveedores_erp.insert("", "end", iid=str(p['id']), values=(p['rut'], p['nombre'], p['contacto'], p['telefono']))

def guardar_proveedor_erp(self):
    from database.proveedores import crear_proveedor, actualizar_proveedor
    nom = self.ent_nom_prov.get()
    rut = self.ent_rut_prov.get()
    tel = self.ent_tel_prov.get()
    cont = self.ent_cont_prov.get()
    
    if not nom or not rut:
        messagebox.showwarning("Error", "Razón Social y RUT son obligatorios")
        return
    try:
        if self.proveedor_seleccionado_id:
            actualizar_proveedor(int(self.proveedor_seleccionado_id), nombre=nom, rut=rut, telefono=tel, contacto=cont)
            registrar_historial(
                accion="Modificación",
                tabla="proveedores",
                referencia_id=int(self.proveedor_seleccionado_id),
                detalles=f"Proveedor actualizado: {nom} (RUT: {rut})",
                usuario_id=Sesion.get_usuario_id()
            )
            messagebox.showinfo("Éxito", "Proveedor actualizado")
        else:
            new_id = crear_proveedor(nombre=nom, rut=rut, telefono=tel, contacto=cont)
            registrar_historial(
                accion="Creación",
                tabla="proveedores",
                referencia_id=new_id,
                detalles=f"Nuevo proveedor registrado: {nom} (RUT: {rut})",
                usuario_id=Sesion.get_usuario_id()
            )
            messagebox.showinfo("Éxito", "Proveedor registrado correctamente")
        
        limpiar_form_proveedor(self)
        actualizar_tabla_proveedores_erp(self)
        refrescar_combos_maestros(self)
    except Exception as e:
        get_logger("compras").exception("Falló al guardar (compras)")
        messagebox.showerror("Error", f"No se pudo guardar: {e}")

def inicializar_tab_config_cuentas(self):
    # Contenedor dividido
    contenedor = tk.Frame(self.tab_config_cuentas, bg=COLOR_GRIS)
    contenedor.pack(fill="both", expand=True)

    col_izq = tk.Frame(contenedor, bg=COLOR_GRIS)
    col_izq.pack(side="left", fill="both", expand=True, padx=(0, 10))
    
    col_der = tk.Frame(contenedor, bg=COLOR_GRIS, width=max(300, escalar(350)))
    col_der.pack(side="right", fill="both", expand=False)
    col_der.pack_propagate(False)

    # --- Tarjeta 1: Listado ---
    tarjeta_lista = render_tarjeta_erp(col_izq, "Plan de Cuentas Contables")
    
    columnas = ("codigo", "nombre", "tipo", "inventariable")
    self.tree_cuentas = ttk.Treeview(tarjeta_lista, columns=columnas, show="headings", style="ERP.Treeview")
    
    self.tree_cuentas.heading("codigo", text="Código")
    self.tree_cuentas.heading("nombre", text="Nombre Cuenta")
    self.tree_cuentas.heading("tipo", text="Tipo")
    self.tree_cuentas.heading("inventariable", text="Inventariable")
    
    self.tree_cuentas.column("codigo", width=escalar(80), anchor="center")
    self.tree_cuentas.column("nombre", width=escalar(250), anchor="w")
    self.tree_cuentas.column("tipo", width=escalar(110), anchor="center")
    self.tree_cuentas.column("inventariable", width=escalar(110), anchor="center")
    
    self.tree_cuentas.pack(fill="both", expand=True)
    
    # Botones
    f_btns = tk.Frame(tarjeta_lista, bg=COLOR_BLANCO)
    f_btns.pack(fill="x", pady=(15, 0))
    
    self.btn_edit_cuenta = tk.Button(f_btns, text="📝 Editar", bg=COLOR_SECUNDARIO, fg=COLOR_BLANCO, relief="flat", font=("Segoe UI", escalar_fuente(9), "bold"), cursor="hand2", state="disabled", command=lambda: cargar_cuenta_en_form(self))
    self.btn_edit_cuenta.pack(side="left", padx=5)
    
    self.btn_del_cuenta = tk.Button(f_btns, text="🗑️ Eliminar", bg="#fee2e2", fg=COLOR_PELIGRO, relief="flat", font=("Segoe UI", escalar_fuente(9), "bold"), cursor="hand2", state="disabled", command=lambda: procesar_eliminar_cuenta(self))
    self.btn_del_cuenta.pack(side="left", padx=5)
    
    # --- Tarjeta 2: Formulario ---
    tarjeta_form = render_tarjeta_erp(col_der, "Nueva Cuenta / Categoría")
    
    f_inputs = tk.Frame(tarjeta_form, bg=COLOR_BLANCO)
    f_inputs.pack(fill="both", expand=True)
    
    self.ent_cod_cuenta = crear_label_input(f_inputs, "Código Contable:", 0)
    
    self.ent_nom_cuenta = crear_label_input(f_inputs, "Nombre de la Cuenta:", 1)
    
    self.cmb_tipo_cuenta = crear_label_input(f_inputs, "Tipo de Cuenta:", 2, is_combo=True, values=["egreso", "activo", "pasivo", "ingreso"])
    self.cmb_tipo_cuenta.set("egreso")
    
    self.chk_inv_cuenta_var = tk.BooleanVar()
    self.chk_inv_cuenta = tk.Checkbutton(f_inputs, text="Afecta Stock / Inventario", variable=self.chk_inv_cuenta_var, bg=COLOR_BLANCO, font=("Segoe UI", escalar_fuente(9)))
    self.chk_inv_cuenta.grid(row=6, column=0, sticky="w", pady=10)
    
    # Ajuste vertical
    for i, w in enumerate(f_inputs.winfo_children()):
        if isinstance(w, tk.Label):
            w.grid(row=i*2, column=0, sticky="w", pady=(10, 0))
        elif isinstance(w, (tk.Entry, ttk.Combobox)):
            w.grid(row=i*2+1, column=0, sticky="ew", pady=(0, 10))
            w.grid_configure(padx=0)
    f_inputs.columnconfigure(0, weight=1)
    
    self.btn_guardar_cuenta = tk.Button(tarjeta_form, text="GUARDAR CUENTA", bg=COLOR_PRIMARIO, fg=COLOR_BLANCO, relief="flat", font=("Segoe UI", escalar_fuente(10), "bold"), cursor="hand2", height=2, command=lambda: guardar_cuenta(self))
    self.btn_guardar_cuenta.pack(fill="x", pady=(10, 5))

    self.btn_cancelar_cuenta = tk.Button(tarjeta_form, text="Cancelar Edición", bg="#f1f5f9", fg="#64748b", relief="flat", font=("Segoe UI", escalar_fuente(9)), cursor="hand2", command=lambda: limpiar_form_cuenta(self))
    self.btn_cancelar_cuenta.pack(fill="x")
    
    self.cuenta_seleccionada_id = None

    # Eventos
    self.tree_cuentas.bind("<<TreeviewSelect>>", lambda e: on_select_cuenta(self))

    actualizar_tabla_cuentas(self)

def on_select_cuenta(self):
    seleccion = self.tree_cuentas.selection()
    if seleccion:
        self.btn_edit_cuenta.config(state="normal")
        self.btn_del_cuenta.config(state="normal")
    else:
        self.btn_edit_cuenta.config(state="disabled")
        self.btn_del_cuenta.config(state="disabled")

def cargar_cuenta_en_form(self):
    seleccion = self.tree_cuentas.selection()
    if not seleccion: return
    
    item = self.tree_cuentas.item(seleccion[0])
    valores = item['values']
    self.cuenta_seleccionada_id = str(seleccion[0])
    
    self.ent_cod_cuenta.delete(0, tk.END)
    self.ent_cod_cuenta.insert(0, valores[0])
    self.ent_nom_cuenta.delete(0, tk.END)
    self.ent_nom_cuenta.insert(0, valores[1])
    self.cmb_tipo_cuenta.set(valores[2])
    self.chk_inv_cuenta_var.set(True if valores[3] == "Sí" else False)
    
    self.btn_guardar_cuenta.config(text="ACTUALIZAR CUENTA", bg="#f39c12")

def limpiar_form_cuenta(self):
    self.cuenta_seleccionada_id = None
    self.ent_cod_cuenta.delete(0, tk.END)
    self.ent_nom_cuenta.delete(0, tk.END)
    self.cmb_tipo_cuenta.set("egreso")
    self.chk_inv_cuenta_var.set(False)
    self.btn_guardar_cuenta.config(text="GUARDAR CUENTA", bg=COLOR_PRIMARIO)

def procesar_eliminar_cuenta(self):
    from database.plan_cuentas import eliminar_cuenta_contable
    seleccion = self.tree_cuentas.selection()
    if not seleccion: return
    
    if messagebox.askyesno("Confirmar", "¿Desea desactivar esta cuenta?"):
        cuenta_id = int(seleccion[0])
        if eliminar_cuenta_contable(cuenta_id):
            messagebox.showinfo("Éxito", "Cuenta desactivada")
            actualizar_tabla_cuentas(self)
        else:
            messagebox.showerror("Error", "No se pudo desactivar")

def actualizar_tabla_cuentas(self):
    from database.plan_cuentas import obtener_plan_cuentas
    self.tree_cuentas.delete(*self.tree_cuentas.get_children())
    for c in obtener_plan_cuentas():
        inv_str = "Sí" if c['es_inventariable'] else "No"
        self.tree_cuentas.insert("", "end", iid=str(c['id']), values=(c['codigo'], c['nombre'], c['tipo'], inv_str))

def guardar_cuenta(self):
    from database.plan_cuentas import crear_cuenta_contable, actualizar_cuenta_contable
    cod = self.ent_cod_cuenta.get()
    nom = self.ent_nom_cuenta.get()
    tipo = self.cmb_tipo_cuenta.get()
    inv = self.chk_inv_cuenta_var.get()
    
    if not cod or not nom:
        messagebox.showwarning("Error", "Código y Nombre son obligatorios")
        return
    try:
        if self.cuenta_seleccionada_id:
            actualizar_cuenta_contable(int(self.cuenta_seleccionada_id), codigo=cod, nombre=nom, tipo=tipo, es_inventariable=inv)
            messagebox.showinfo("Éxito", "Cuenta actualizada")
        else:
            crear_cuenta_contable(cod, nom, tipo, inv)
            messagebox.showinfo("Éxito", "Cuenta creada correctamente")
            
        limpiar_form_cuenta(self)
        actualizar_tabla_cuentas(self)
        refrescar_combos_maestros(self)
    except Exception as e:
        get_logger("compras").exception("Falló al guardar (compras)")
        messagebox.showerror("Error", f"No se pudo guardar: {e}")
