import tkinter as tk

from ui_scale import escalar, escalar_fuente
from modulos.utils_globales import crear_frame_scrollable
from config import COLOR_PRIMARIO, COLOR_BLANCO, COLOR_GRIS, COLOR_PELIGRO, FUENTE_BOTON, FUENTE_MODULO

class ConfiguracionUI:
    def __init__(self, parent_frame, on_section_select, volver_menu_callback):
        self.parent = parent_frame
        self.on_section_select = on_section_select
        self.volver_menu = volver_menu_callback
        
        self.btn_activos = {}
        self.construir_layout()
        
    def construir_layout(self):
        for widget in self.parent.winfo_children():
            widget.destroy()
            
        # Header
        self.header = tk.Frame(self.parent, bg=COLOR_PRIMARIO, height=escalar(70))
        self.header.pack(fill="x", side="top")
        self.header.pack_propagate(False)
        
        tk.Label(
            self.header, text="⚙️  CONFIGURACIÓN", 
            font=FUENTE_MODULO, fg=COLOR_BLANCO, bg=COLOR_PRIMARIO
        ).pack(side="left", padx=escalar(20), pady=escalar(18))
        
        tk.Button(
            self.header, text="← Volver al Menú", bg=COLOR_PELIGRO, fg=COLOR_BLANCO,
            relief="flat", font=FUENTE_BOTON, cursor="hand2", command=self.volver_menu
        ).pack(side="right", padx=escalar(20), pady=escalar(18))
        
        # Contenedor Cuerpo
        self.body = tk.Frame(self.parent, bg=COLOR_GRIS)
        self.body.pack(fill="both", expand=True)
        
        # Sidebar
        self.sidebar = tk.Frame(self.body, bg="#f8fafc", width=max(240, escalar(280)), bd=0)
        self.sidebar.pack(side="left", fill="y", padx=0, pady=0)
        self.sidebar.pack_propagate(False)
        
        tk.Frame(self.sidebar, width=1, bg="#e2e8f0").pack(side="right", fill="y")
        
        tk.Label(self.sidebar, text="NAVEGACIÓN", font=("Segoe UI", escalar_fuente(10), "bold"), bg="#f8fafc", fg="#94a3b8").pack(anchor="w", padx=escalar(25), pady=(escalar(30), escalar(15)))
        
        # Panel derecho
        panel_shell = tk.Frame(self.body, bg=COLOR_GRIS)
        panel_shell.pack(side="left", fill="both", expand=True, padx=escalar(15), pady=escalar(15))
        scroll_panel, self.panel_derecho = crear_frame_scrollable(panel_shell, bg=COLOR_GRIS)
        scroll_panel.pack(fill="both", expand=True)
        
        self.opciones = [
            ("🏢", "Empresa", "empresa"),
            ("🧾", "Finanzas", "finanzas"),
            ("🗄", "Backup", "sistema"),
            ("ℹ", "Acerca de", "acerca_de")
        ]
        
        self._construir_menu()
        
    def _construir_menu(self):
        for icon, texto, slug in self.opciones:
            btn = tk.Frame(self.sidebar, bg="#f8fafc", cursor="hand2")
            btn.pack(fill="x", padx=escalar(10), pady=escalar(2))
            
            lbl_icon = tk.Label(btn, text=icon, font=("Segoe UI", escalar_fuente(13)), bg="#f8fafc", fg="#94a3b8", cursor="hand2", width=3)
            lbl_icon.pack(side="left", pady=escalar(12), padx=(escalar(15), escalar(5)))
            
            lbl_text = tk.Label(btn, text=texto, font=("Segoe UI", escalar_fuente(10)), bg="#f8fafc", fg="#475569", cursor="hand2")
            lbl_text.pack(side="left", pady=escalar(12))
            
            def on_click(e, s=slug):
                self.marcar_activo(s)
                self.on_section_select(s)
                
            def on_enter(e, s=slug, b=btn, lt=lbl_text, li=lbl_icon):
                if not self.btn_activos.get(s, False):
                    b.config(bg="#f1f5f9")
                    lt.config(bg="#f1f5f9")
                    li.config(bg="#f1f5f9")
                    
            def on_leave(e, s=slug, b=btn, lt=lbl_text, li=lbl_icon):
                if not self.btn_activos.get(s, False):
                    b.config(bg="#f8fafc")
                    lt.config(bg="#f8fafc")
                    li.config(bg="#f8fafc")

            for w in (btn, lbl_icon, lbl_text):
                w.bind("<Button-1>", on_click)
                w.bind("<Enter>", on_enter)
                w.bind("<Leave>", on_leave)
                
            self.btn_activos[slug] = False
            setattr(self, f"_menu_{slug}", (btn, lbl_icon, lbl_text))
            
    def marcar_activo(self, slug_activo):
        for slug in self.btn_activos.keys():
            self.btn_activos[slug] = (slug == slug_activo)
            b, li, lt = getattr(self, f"_menu_{slug}")
            b.config(bg="#f8fafc")
            li.config(bg="#f8fafc", fg="#94a3b8")
            lt.config(bg="#f8fafc", fg="#475569", font=("Segoe UI", escalar_fuente(10)))
            
        b, li, lt = getattr(self, f"_menu_{slug_activo}")
        b.config(bg="#e0f2fe")
        li.config(bg="#e0f2fe", fg=COLOR_PRIMARIO)
        lt.config(bg="#e0f2fe", fg=COLOR_PRIMARIO, font=("Segoe UI", escalar_fuente(10), "bold"))

    def limpiar_panel_derecho(self):
        for widget in self.panel_derecho.winfo_children():
            widget.destroy()
            
    def render_tarjeta(self, parent, titulo):
        frame = tk.Frame(parent, bg=COLOR_BLANCO, bd=1, relief="solid")
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text=titulo, font=("Segoe UI", escalar_fuente(14), "bold"), bg=COLOR_BLANCO, fg=COLOR_PRIMARIO).pack(anchor="w", padx=escalar(25), pady=(escalar(20), escalar(10)))
        tk.Frame(frame, height=1, bg="#eee").pack(fill="x", padx=escalar(25), pady=(0, escalar(20)))
        
        contenido = tk.Frame(frame, bg=COLOR_BLANCO)
        contenido.pack(fill="both", expand=True, padx=escalar(25), pady=(0, escalar(25)))
        return contenido
