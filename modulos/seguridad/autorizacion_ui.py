import tkinter as tk
from tkinter import messagebox
from .auth import validar_admin
from modulos.utils_globales import aplicar_barra_windows_azul, centrar_ventana_mejorado, preparar_modal_scrollable
from ui_scale import escalar_fuente

class ModalAutorizacion(tk.Toplevel):
    def __init__(self, parent, accion="esta acción"):
        super().__init__(parent)
        self.withdraw() # Ocultar mientras se construye
        self.title("Sistema de Seguridad")
        # No ponemos geometry aqui para dejar que centrar_ventana_mejorado lo maneje
        self.resizable(False, False)
        self.configure(bg="#f8f9fa")
        aplicar_barra_windows_azul(self)
        self.transient(parent)
        self.grab_set()
        
        self.autorizado = False
        self.accion = accion
        
        self.construir_ui()
        from ui_scale import escalar
        centrar_ventana_mejorado(self, escalar(400), escalar(420), relativo_a=parent)



    def construir_ui(self):
        # Configuración de colores HUD OSCURO (Alta visibilidad)
        COLOR_ACCENTO = "#ef4444" # Rojo vibrante
        COLOR_FONDO_MODAL = "#0f172a" # Slate muy oscuro
        COLOR_FONDO_CARD = "#1e293b" # Slate oscuro
        COLOR_TEXTO_PRINCIPAL = "#ffffff"
        COLOR_TEXTO_SECUNDARIO = "#94a3b8"

        self.configure(bg=COLOR_FONDO_MODAL)

        # --- HEADER DE COLOR ---
        frame_header = tk.Frame(self, bg=COLOR_ACCENTO, height=4)
        frame_header.pack(fill="x")
        
        # Contenedor principal con padding y auto-scroll
        scroll_body = preparar_modal_scrollable(self, bg=COLOR_FONDO_MODAL)
        body = tk.Frame(scroll_body, bg=COLOR_FONDO_MODAL, padx=35, pady=30)
        body.pack(fill="both", expand=True)

        # Icono HUD
        tk.Label(
            body, text="🔒", font=("Segoe UI", escalar_fuente(40, maximo=60)),
            bg=COLOR_FONDO_MODAL, fg=COLOR_ACCENTO
        ).pack(pady=(0, 15))

        tk.Label(
            body, text="ACCESO RESTRINGIDO",
            font=("Segoe UI", escalar_fuente(13), "bold"), bg=COLOR_FONDO_MODAL, fg=COLOR_TEXTO_PRINCIPAL
        ).pack()

        tk.Label(
            body, text=f"Se requiere autorización para:\n{self.accion}",
            font=("Segoe UI", escalar_fuente(9)), bg=COLOR_FONDO_MODAL, fg=COLOR_TEXTO_SECUNDARIO,
            justify="center"
        ).pack(pady=(5, 20))

        # Campo de Entrada Estilo HUD
        frame_input = tk.Frame(body, bg=COLOR_FONDO_MODAL)
        frame_input.pack(fill="x")

        tk.Label(
            frame_input, text="CONTRASEÑA DE ADMINISTRADOR", 
            bg=COLOR_FONDO_MODAL, fg=COLOR_ACCENTO, font=("Segoe UI", escalar_fuente(8), "bold")
        ).pack(anchor="center", pady=(0, 8))

        self.ent_pass = tk.Entry(
            frame_input, show="*", font=("Segoe UI", escalar_fuente(14), "bold"), 
            justify="center", relief="flat", bd=0, 
            bg=COLOR_FONDO_CARD, fg=COLOR_TEXTO_PRINCIPAL,
            insertbackground="white" # Cursor blanco para fondo oscuro
        )
        self.ent_pass.pack(fill="x", ipady=10)
        
        # Aplicar estilo de foco personalizado para modo oscuro
        from modulos.utils_globales import configurar_focus_entry
        configurar_focus_entry(self.ent_pass, color_normal=COLOR_FONDO_CARD)
        
        self.ent_pass.focus_set()
        
        # --- BOTONES HUD ---
        btns = tk.Frame(body, bg=COLOR_FONDO_MODAL)
        btns.pack(fill="x", pady=(25, 0))

        self.btn_validar = tk.Button(
            btns, text="ENTER ➔", bg="#22c55e", fg="white",
            relief="flat", font=("Segoe UI", escalar_fuente(10), "bold"), cursor="hand2",
            activebackground="#16a34a", activeforeground="white"
        )
        self.btn_validar.config(command=self.validar)
        self.btn_validar.pack(side="left", expand=True, fill="x", padx=(0, 5), ipady=10)

        tk.Button(
            btns, text="CANCELAR", bg=COLOR_FONDO_CARD, fg=COLOR_TEXTO_SECUNDARIO,
            relief="flat", font=("Segoe UI", escalar_fuente(9)), cursor="hand2",
            activebackground="#334155", activeforeground="white",
            command=self.destroy
        ).pack(side="left", expand=True, fill="x", ipady=10)

        # Shortcuts (Añadido soporte para teclado numérico)
        self.bind("<Return>", lambda e: self.validar())
        self.bind("<KP_Enter>", lambda e: self.validar())
        self.bind("<Escape>", lambda e: self.destroy())

    def validar(self):
        pwd = self.ent_pass.get()
        if validar_admin(pwd):
            self.autorizado = True
            _registrar_en_historial(self.accion, "Autorizado por Admin")
            self.destroy()
        else:
            messagebox.showerror("Error", "Contraseña de administrador incorrecta.")
            self.ent_pass.delete(0, tk.END)


# Cuánto dura la autorización antes de volver a pedir la contraseña.
# Solo aplica a las llamadas que declaran un `ambito`.
VENTANA_GRACIA_SEGUNDOS = 60


def _registrar_en_historial(accion, nota):
    """Deja el rastro de auditoría. Nunca interrumpe la operación."""
    try:
        from database.historial import registrar_historial
        from modulos.seguridad.sesion import Sesion

        registrar_historial(
            accion="autorizacion_admin",
            tabla="seguridad",
            referencia_id=None,
            detalles=f"Acción: {accion} | {nota}",
            usuario_id=Sesion.get_usuario_id()
        )
    except Exception as e:
        from vim_logger import get_logger
        get_logger("seguridad.autorizacion").warning(
            f"No se pudo registrar la autorización en el historial: {e}"
        )


def solicitar_autorizacion_admin(parent, accion="continuar", ambito=None,
                                 segundos_gracia=VENTANA_GRACIA_SEGUNDOS):
    """Pide la contraseña de administrador y retorna True/False.

    Si se indica `ambito`, la autorización queda vigente `segundos_gracia`
    segundos: repetir la MISMA acción dentro de ese lapso no vuelve a pedir
    la contraseña. Sirve para tareas en tanda (ej. depurar varios productos).

    La vigencia es por ámbito, así que autorizar un borrado de productos no
    habilita anular ventas ni restaurar la base. Sin `ambito` el
    comportamiento es el de siempre: se pide la contraseña cada vez.
    """
    from modulos.seguridad.sesion import Sesion

    if ambito and Sesion.autorizacion_vigente(ambito, segundos_gracia):
        restantes = Sesion.segundos_restantes_autorizacion(ambito, segundos_gracia)
        _registrar_en_historial(
            accion, f"Autorización vigente ({restantes}s restantes, sin pedir contraseña)"
        )
        return True

    modal = ModalAutorizacion(parent, accion)
    parent.wait_window(modal)

    if modal.autorizado and ambito:
        Sesion.registrar_autorizacion(ambito)

    return modal.autorizado
