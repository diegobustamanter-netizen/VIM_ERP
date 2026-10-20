import tkinter as tk
from tkinter import ttk, messagebox
from ...configuracion.utils import get_configs, set_config
from database.utils import ahora

from ui_scale import escalar, escalar_fuente
from vim_logger import get_logger

class EmpresaSeccion:
    def __init__(self, parent, ui):
        self.parent = parent
        self.ui = ui
        
        # Obtenemos las configuraciones actuales
        claves = [
            "nombre_negocio", "rut_empresa", "giro_empresa", 
            "direccion_empresa", "telefono_empresa", "email_empresa", 
            "moneda", "ticket_tamano", "ticket_logo", "ticket_desglose_iva",
            "ticket_mensaje_pie", "ticket_copias", "iva_porcentaje",
            "impresora_termica", "impresion_automatica"
        ]
        self.config_actual = get_configs(claves)
        
        # Valores por defecto si no existen
        if not self.config_actual.get("ticket_tamano"):
            self.config_actual["ticket_tamano"] = "58mm"
        if not self.config_actual.get("ticket_mensaje_pie"):
            self.config_actual["ticket_mensaje_pie"] = "¡Gracias por su compra!"
            
        self.construir_ui()
        self.actualizar_preview()

    def construir_ui(self):
        for w in self.parent.winfo_children():
            w.destroy()
            
        # Contenedor principal simple
        container = tk.Frame(self.parent, bg="#f4f6f9")
        container.pack(fill="both", expand=True)
        
        # Contenedor izquierdo (formulario)
        frame_izq = tk.Frame(container, bg="#f4f6f9")
        frame_izq.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        # Tarjeta del formulario
        frame_form = self.ui.render_tarjeta(frame_izq, "🏢 Información Comercial")
        
        # Grid para los campos
        f_grid = tk.Frame(frame_form, bg="white")
        f_grid.pack(fill="both", expand=False)
        f_grid.grid_columnconfigure(1, weight=1)
        
        campos = [
            ("Razón Social / Nombre:", "ent_nombre", "nombre_negocio", 35),
            ("RUT Empresa:", "ent_rut", "rut_empresa", 20),
            ("Giro Comercial:", "ent_giro", "giro_empresa", 35),
            ("Dirección Física:", "ent_direccion", "direccion_empresa", 35),
            ("Teléfono Local:", "ent_telefono", "telefono_empresa", 20),
            ("Email Corporativo:", "ent_email", "email_empresa", 30),
        ]
        
        for i, (label_text, attr_name, config_key, width) in enumerate(campos):
            tk.Label(f_grid, text=label_text, bg="white", font=("Segoe UI", escalar_fuente(9), "bold")).grid(row=i, column=0, sticky="w", pady=8, padx=(0, 10))
            ent = tk.Entry(f_grid, width=width, font=("Segoe UI", escalar_fuente(10)))
            ent.grid(row=i, column=1, padx=0, pady=8, sticky="ew")
            
            val = self.config_actual.get(config_key)
            if val: ent.insert(0, val)
            
            setattr(self, attr_name, ent)
            
        # Boton guardar general
        btn_guardar = tk.Button(
            f_grid, text="💾 Guardar Todos Los Cambios", bg="#28a745", fg="white", cursor="hand2", 
            relief="flat", font=("Segoe UI", escalar_fuente(11), "bold"), command=self.guardar
        )
        btn_guardar.grid(row=len(campos)+1, column=0, columnspan=2, pady=(20, 0), sticky="ew", ipady=8)

        # --- DERECHA: Configuración de Ticket y Vista Previa ---
        frame_der = tk.Frame(container, bg="white", bd=1, relief="solid")
        frame_der.pack(side="right", fill="y", padx=(10, 0))

        
        tk.Label(frame_der, text="🧾 Diseño y Preferencias", bg="white", fg="#002b5c", font=("Segoe UI", escalar_fuente(13), "bold")).pack(pady=(20, 10))
        tk.Frame(frame_der, height=1, bg="#eee").pack(fill="x", padx=20)
        
        # Opciones del ticket
        f_opc = tk.Frame(frame_der, bg="white")
        f_opc.pack(fill="x", padx=20, pady=10)
        
        # Fila 1: Ancho y Copias
        f_f1 = tk.Frame(f_opc, bg="white")
        f_f1.pack(fill="x", pady=5)
        
        tk.Label(f_f1, text="Papel:", bg="white", font=("Segoe UI", escalar_fuente(9), "bold")).pack(side="left")
        self.cmb_ancho = ttk.Combobox(f_f1, values=["58mm", "80mm"], state="readonly", width=8, font=("Segoe UI", escalar_fuente(10)))
        self.cmb_ancho.pack(side="left", padx=5)
        self.cmb_ancho.set(self.config_actual.get("ticket_tamano", "58mm"))
        self.cmb_ancho.bind("<<ComboboxSelected>>", lambda e: self.actualizar_preview())
        
        tk.Label(f_f1, text="Copias:", bg="white", font=("Segoe UI", escalar_fuente(9), "bold")).pack(side="left", padx=(10, 0))
        self.spin_copias = tk.Spinbox(f_f1, from_=1, to=5, width=3)
        self.spin_copias.pack(side="left", padx=5)
        self.spin_copias.delete(0, tk.END)
        self.spin_copias.insert(0, self.config_actual.get("ticket_copias") or "1")
        
        # Fila 2: Checkboxes
        f_f2 = tk.Frame(f_opc, bg="white")
        f_f2.pack(fill="x", pady=5)
        
        self.var_iva = tk.BooleanVar(value=str(self.config_actual.get("ticket_desglose_iva", "1")) in ("1", "True", "true"))
        tk.Checkbutton(f_f2, text="IVA", variable=self.var_iva, bg="white", font=("Segoe UI", escalar_fuente(8)), command=self.actualizar_preview).pack(side="left")
        
        btn_actualizar_prev = tk.Button(
            f_f2, text="🔄 Actualizar Vista", bg="#17a2b8", fg="white", cursor="hand2", 
            relief="flat", font=("Segoe UI", escalar_fuente(8), "bold"), command=self.actualizar_preview
        )
        btn_actualizar_prev.pack(side="right")
        
        # Fila 3: Mensaje pie
        tk.Label(f_opc, text="Mensaje de pie:", bg="white", font=("Segoe UI", escalar_fuente(9), "bold")).pack(anchor="w")
        self.ent_pie = tk.Entry(f_opc, font=("Segoe UI", escalar_fuente(9)))
        self.ent_pie.pack(fill="x", pady=(2, 10))
        self.ent_pie.insert(0, self.config_actual.get("ticket_mensaje_pie") or "¡Gracias por su compra!")

        # ── Impresora térmica ────────────────────────────────
        tk.Frame(f_opc, height=1, bg="#eee").pack(fill="x", pady=(4, 8))
        tk.Label(f_opc, text="🖨 Impresora térmica (58/80mm):", bg="white",
                 font=("Segoe UI", escalar_fuente(9), "bold")).pack(anchor="w")

        f_imp = tk.Frame(f_opc, bg="white")
        f_imp.pack(fill="x", pady=(2, 4))

        self.cmb_impresora = ttk.Combobox(f_imp, state="readonly", width=24,
                                          font=("Segoe UI", escalar_fuente(9)))
        self.cmb_impresora.pack(side="left", fill="x", expand=True)
        # La impresora se guarda apenas se elige. Antes solo se guardaba con
        # el botón "Guardar Todos Los Cambios" del panel izquierdo, lejos de
        # este combo: si no se apretaba, la elección se perdía.
        self.cmb_impresora.bind("<<ComboboxSelected>>", lambda e: self._guardar_impresora())

        tk.Button(
            f_imp, text="🔄", bg="#e2e8f0", relief="flat", cursor="hand2",
            font=("Segoe UI", escalar_fuente(9)), command=self._cargar_impresoras
        ).pack(side="left", padx=(4, 0))

        self._cargar_impresoras()

        self.var_impresion_auto = tk.BooleanVar(
            value=str(self.config_actual.get("impresion_automatica", "1")) in ("1", "True", "true", "")
        )
        tk.Checkbutton(
            f_imp2 := tk.Frame(f_opc, bg="white"), text="Imprimir al confirmar cada venta",
            variable=self.var_impresion_auto, bg="white", font=("Segoe UI", escalar_fuente(8))
        ).pack(side="left")
        f_imp2.pack(fill="x")

        # Sin impresora térmica igual se puede ver cómo queda el comprobante
        tk.Button(
            f_imp2, text="📄 Vista previa", bg="#64748b", fg="white", cursor="hand2",
            relief="flat", font=("Segoe UI", escalar_fuente(8), "bold"),
            command=self._vista_previa_pdf
        ).pack(side="right", padx=(4, 0))

        tk.Button(
            f_imp2, text="🖨 Imprimir prueba", bg="#0ea5e9", fg="white", cursor="hand2",
            relief="flat", font=("Segoe UI", escalar_fuente(8), "bold"),
            command=self._imprimir_prueba
        ).pack(side="right")

        # Contenedor gris oscuro (fondo simulando mesa)
        mesa = tk.Frame(frame_der, bg="#cbd5e1")
        mesa.pack(fill="both", expand=True, padx=20, pady=(10, 20))
        
        # El ticket de papel (blanco) con márgenes realistas
        self.ticket_canvas = tk.Frame(mesa, bg="white", bd=0)
        self.ticket_canvas.pack(pady=10, padx=10)
        
        self.ticket_spacer = tk.Frame(self.ticket_canvas, bg="white", height=1)
        self.ticket_spacer.pack(fill="x")
        
        # Labels del ticket con márgenes internos proporcionales
        self.lbl_t_nombre = tk.Label(self.ticket_canvas, bg="white", font=("Courier New", escalar_fuente(14), "bold"), justify="center")
        self.lbl_t_nombre.pack(fill="x", pady=(8, 2), padx=5)
        
        self.lbl_t_rut = tk.Label(self.ticket_canvas, bg="white", font=("Courier New", escalar_fuente(9)), justify="center")
        self.lbl_t_rut.pack(fill="x", pady=0, padx=5)
        
        self.lbl_t_giro = tk.Label(self.ticket_canvas, bg="white", font=("Courier New", escalar_fuente(8)), justify="center")
        self.lbl_t_giro.pack(fill="x", pady=(2, 0), padx=5)
        
        self.lbl_t_dir = tk.Label(self.ticket_canvas, bg="white", font=("Courier New", escalar_fuente(8)), justify="center")
        self.lbl_t_dir.pack(fill="x", pady=(2, 0), padx=5)
        
        self.lbl_t_tel = tk.Label(self.ticket_canvas, bg="white", font=("Courier New", escalar_fuente(8)), justify="center")
        self.lbl_t_tel.pack(fill="x", pady=0, padx=5)
        
        self.lbl_t_sep = tk.Label(self.ticket_canvas, bg="white", font=("Courier New", escalar_fuente(9)))
        self.lbl_t_sep.pack(fill="x", pady=(5, 5), padx=5)
        
        # Datos simulados de venta
        f_det = tk.Frame(self.ticket_canvas, bg="white")
        f_det.pack(fill="x", padx=8)
        
        self.lbl_t_fecha = tk.Label(f_det, bg="white", font=("Courier New", escalar_fuente(8)), justify="left")
        self.lbl_t_fecha.pack(anchor="w")
        
        tk.Label(f_det, text="Cajero: Admin   Caja: 01", bg="white", font=("Courier New", escalar_fuente(8))).pack(anchor="w")
        
        self.lbl_t_sep2 = tk.Label(self.ticket_canvas, bg="white", font=("Courier New", escalar_fuente(9)))
        self.lbl_t_sep2.pack(fill="x", pady=(5, 5), padx=5)
        
        # Items simulados
        f_items = tk.Frame(self.ticket_canvas, bg="white")
        f_items.pack(fill="x", padx=8)
        self.lbl_t_items = tk.Label(f_items, bg="white", font=("Courier New", escalar_fuente(9)), justify="left")
        self.lbl_t_items.pack(anchor="w")
        
        # Breakdown IVA (Simulado)
        self.lbl_t_iva = tk.Label(self.ticket_canvas, bg="white", font=("Courier New", escalar_fuente(8)), justify="right", fg="#444")
        # Se packeara en actualizar_preview

        self.lbl_t_sep3 = tk.Label(self.ticket_canvas, bg="white", font=("Courier New", escalar_fuente(9)))
        self.lbl_t_sep3.pack(fill="x", pady=(5, 5), padx=5)
        
        # Total
        self.lbl_t_total = tk.Label(self.ticket_canvas, bg="white", font=("Courier New", escalar_fuente(12), "bold"), justify="right")
        self.lbl_t_total.pack(anchor="e", padx=8, pady=(0, 5))

        # Mensaje de pie (Simulado)
        self.lbl_t_pie = tk.Label(self.ticket_canvas, bg="white", font=("Courier New", escalar_fuente(8)), justify="center", wraplength=escalar(200))
        self.lbl_t_pie.pack(fill="x", pady=(5, 10), padx=5)


    def _cargar_impresoras(self):
        """Llena el combobox con las impresoras instaladas en Windows."""
        try:
            from modulos.impresion import listar_impresoras
            impresoras = listar_impresoras()
        except Exception:
            get_logger("configuracion.empresa").exception("No se pudo listar las impresoras")
            impresoras = []

        self.cmb_impresora["values"] = ["(Sin impresora)"] + impresoras

        guardada = (self.config_actual.get("impresora_termica") or "").strip()
        if guardada and guardada in impresoras:
            self.cmb_impresora.set(guardada)
        elif guardada:
            # La guardada ya no existe: mostrarla igual para que el usuario note el problema
            self.cmb_impresora["values"] = ["(Sin impresora)"] + impresoras + [guardada]
            self.cmb_impresora.set(guardada)
        else:
            self.cmb_impresora.set("(Sin impresora)")

    def _vista_previa_pdf(self):
        """Abre un PDF con un comprobante de ejemplo, con los datos actuales
        del formulario (aunque todavía no se hayan guardado)."""
        import os
        import tempfile
        from modulos.impresion import guardar_ticket_pdf, datos_de_ejemplo

        config = dict(self.config_actual)
        config.update({
            "nombre_negocio": self.ent_nombre.get().strip(),
            "rut_empresa": self.ent_rut.get().strip(),
            "giro_empresa": self.ent_giro.get().strip(),
            "direccion_empresa": self.ent_direccion.get().strip(),
            "telefono_empresa": self.ent_telefono.get().strip(),
            "ticket_tamano": self.cmb_ancho.get(),
            "ticket_desglose_iva": "1" if self.var_iva.get() else "0",
            "ticket_mensaje_pie": self.ent_pie.get().strip(),
        })
        ruta = os.path.join(tempfile.gettempdir(), "vim_erp_vista_previa.pdf")
        try:
            guardar_ticket_pdf(datos_de_ejemplo(), ruta, config)
            os.startfile(ruta)
        except Exception as e:
            get_logger("configuracion.empresa").exception("No se pudo abrir la vista previa")
            messagebox.showerror(
                "Vista previa",
                f"No se pudo generar o abrir la vista previa:\n{e}\n\n"
                "Si el PDF se guardó, está en:\n" + ruta,
                parent=self.parent)

    def _guardar_impresora(self):
        impresora = self._impresora_seleccionada()
        if set_config("impresora_termica", impresora):
            self.config_actual["impresora_termica"] = impresora

    def _impresora_seleccionada(self):
        val = (self.cmb_impresora.get() or "").strip()
        return "" if val in ("", "(Sin impresora)") else val

    def _imprimir_prueba(self):
        impresora = self._impresora_seleccionada()
        if not impresora:
            messagebox.showwarning(
                "Sin impresora",
                "Seleccione primero una impresora de la lista.\n\n"
                "Si su impresora térmica no aparece, instálela en Windows "
                "(Configuración → Bluetooth y dispositivos → Impresoras) y "
                "luego presione el botón 🔄.",
                parent=self.parent
            )
            return
        try:
            from modulos.impresion import imprimir_pagina_prueba
            imprimir_pagina_prueba(impresora, self.cmb_ancho.get())
            messagebox.showinfo(
                "Prueba enviada",
                f"Se envió una página de prueba a:\n{impresora}\n\n"
                "Si no imprime nada, verifique que la impresora esté encendida, "
                "con papel, y que sea una impresora térmica ESC/POS (la mayoría "
                "de las de 58mm y 80mm lo son).",
                parent=self.parent
            )
        except Exception as e:
            messagebox.showerror(
                "Error de impresión",
                f"No se pudo imprimir la página de prueba:\n\n{e}",
                parent=self.parent
            )

    def actualizar_preview(self):
        nombre = self.ent_nombre.get().strip().upper() or "NOMBRE EMPRESA"
        rut = self.ent_rut.get().strip() or "RUT: 11.111.111-1"
        giro = self.ent_giro.get().strip()
        direccion = self.ent_direccion.get().strip()
        tel = self.ent_telefono.get().strip()
        ancho = self.cmb_ancho.get()
        moneda = "$"
        pie_txt = self.ent_pie.get().strip()
        
        # Tamaños proporcionales reales: 58mm ≈ 230px, 80mm ≈ 315px (a 96 DPI)
        pixeles = escalar(230) if ancho == "58mm" else escalar(315)
        char_limit = 32 if ancho == "58mm" else 48
        sep_char = "-" * char_limit
        
        self.ticket_spacer.config(width=pixeles)
        
        self.lbl_t_nombre.config(text=nombre, wraplength=pixeles - escalar(20))
        # Re-pack nombre para asegurar orden
        self.lbl_t_nombre.pack(fill="x", pady=(5, 2))
        
        self.lbl_t_rut.config(text=f"RUT: {rut}" if not rut.upper().startswith("RUT") else rut)
        
        self.lbl_t_giro.config(text=giro, wraplength=pixeles - escalar(20))
        if giro: self.lbl_t_giro.pack(fill="x", pady=(2, 0))
        else: self.lbl_t_giro.pack_forget()
            
        self.lbl_t_dir.config(text=direccion, wraplength=pixeles - escalar(20))
        if direccion: self.lbl_t_dir.pack(fill="x", pady=(2, 0))
        else: self.lbl_t_dir.pack_forget()
            
        self.lbl_t_tel.config(text=f"Tel: {tel}" if tel else "")
        if tel: self.lbl_t_tel.pack(fill="x", pady=0)
        else: self.lbl_t_tel.pack_forget()
            
        self.lbl_t_sep.config(text=sep_char)
        self.lbl_t_sep2.config(text=sep_char)
        self.lbl_t_sep3.config(text=sep_char)
        
        ahora_str = ahora("%d/%m/%Y %H:%M")
        self.lbl_t_fecha.config(text=f"Fecha: {ahora_str}")
        
        if ancho == "58mm":
            items_txt = f"1x PRODUCTO EJEMPLO\n   {moneda}10.000"
        else:
            items_txt = f"1x PRODUCTO EJEMPLO             {moneda}10.000"
            
        self.lbl_t_items.config(text=items_txt)

        # IVA Breakdown
        if self.var_iva.get():
            neto = 8403
            # Usar el IVA real configurado (antes la clave no se pedía en
            # get_configs y siempre se mostraba 19%)
            try:
                iva_pct = float(self.config_actual.get("iva_porcentaje") or "19")
            except ValueError:
                iva_pct = 19.0
            iva_val = neto * (iva_pct / 100)
            iva_pct_txt = f"{iva_pct:g}"  # 19 → "19", 19.5 → "19.5"
            iva_txt = f"NETO: {moneda}{neto:,.0f}\nIVA ({iva_pct_txt}%): {moneda}{iva_val:,.0f}"
            self.lbl_t_iva.config(text=iva_txt.replace(",", "."))
            self.lbl_t_iva.pack(anchor="e", padx=10, pady=(5, 0))
        else:
            self.lbl_t_iva.pack_forget()

        self.lbl_t_total.config(text=f"TOTAL: {moneda}10.000")
        
        self.lbl_t_pie.config(text=pie_txt, wraplength=pixeles - escalar(20))

    def guardar(self):
        # Información comercial
        set_config("nombre_negocio", self.ent_nombre.get().strip())
        set_config("rut_empresa", self.ent_rut.get().strip())
        set_config("giro_empresa", self.ent_giro.get().strip())
        set_config("direccion_empresa", self.ent_direccion.get().strip())
        set_config("telefono_empresa", self.ent_telefono.get().strip())
        set_config("email_empresa", self.ent_email.get().strip())
        
        # Configuración de ticket (unificada)
        set_config("ticket_tamano", self.cmb_ancho.get())
        # Validar copias: el Spinbox permite escribir texto libre
        try:
            copias = max(1, min(5, int(self.spin_copias.get())))
        except (ValueError, TypeError):
            copias = 1
        set_config("ticket_copias", str(copias))
        set_config("ticket_desglose_iva", "1" if self.var_iva.get() else "0")
        set_config("ticket_mensaje_pie", self.ent_pie.get().strip())

        # Impresora térmica
        self._guardar_impresora()
        set_config("impresion_automatica", "1" if self.var_impresion_auto.get() else "0")
        
        messagebox.showinfo("Éxito", "Configuración de la empresa y tickets guardada correctamente.", parent=self.parent)
