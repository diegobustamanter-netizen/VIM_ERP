import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk
import os

from .auth import autenticar_usuario
from .rate_limiter import limiter
from .sesion import Sesion
from config import COLOR_PRIMARIO, COLOR_SECUNDARIO, COLOR_BLANCO, LOGO_PATH, ICO_PATH
from database.connection import session_db
from modulos.utils_globales import aplicar_barra_windows_azul, centrar_ventana_mejorado, preparar_modal_scrollable
from ui_scale import escalar, escalar_fuente

class VentanaLogin:
    def __init__(self, root, on_login_success, mostrar=True):
        self.root = root
        self.on_success = on_login_success
        
        # Ocultar ventana principal mientras estamos en login
        self.root.withdraw()
        
        self.top = tk.Toplevel(root)
        self.top.withdraw() # Ocultar mientras se construye
        self.top.title("VIM ERP - Acceso al Sistema")
        self.top.resizable(False, False)
        self.top.configure(bg=COLOR_BLANCO)
        aplicar_barra_windows_azul(self.top)
        
        self.construir_ui()

        # Centrar sobre el monitor donde está root, no solo el primario
        from ui_scale import escalar
        # Sin relativo_a: la ventana principal está oculta (tamaño 1x1 en la
        # esquina), y centrar "sobre ella" dejaba el login pegado a la izquierda.
        # Así se centra en el área útil del monitor.
        # Alto según el contenido real: con un alto fijo de 680 todo quedaba
        # pegado arriba y sobraba una franja blanca abajo (se veía corrido).
        self.top.update_idletasks()
        alto = self.main.winfo_reqheight()
        centrar_ventana_mejorado(self.top, escalar(500), alto, mostrar=False)
        self.top.parent = self.root # Evitar recolección de basura
        if mostrar:
            self.mostrar()
        
        # Manejar cierre de ventana (salir de app completa)
        self.top.protocol("WM_DELETE_WINDOW", self.root.quit)

    def mostrar(self):
        """Muestra el login ya construido (el inicio lo llama al cerrar el splash)."""
        # Ícono propio de esta ventana: no depender del ícono por defecto,
        # que se pierde cuando se cierra el splash.
        try:
            if os.path.exists(ICO_PATH):
                self.top.iconbitmap(ICO_PATH)
        except tk.TclError:
            pass
        self.top.deiconify()
        self.top.lift()
        self.top.focus_force()



    def construir_ui(self):
        # Contenedor principal con scroll visual y adaptativo
        main = preparar_modal_scrollable(self.top, bg=COLOR_BLANCO, centrar_vertical=True)
        self.main = main

        # Zona superior — logo
        logo_frame = tk.Frame(main, bg=COLOR_BLANCO)
        logo_frame.pack(fill="x", pady=(escalar(44), escalar(14)))

        if os.path.exists(LOGO_PATH):
            try:
                from modulos.utils_globales import cargar_logo_recortado
                img = cargar_logo_recortado(LOGO_PATH, escalar(280), escalar(90))
                self.logo_img = ImageTk.PhotoImage(img)
                tk.Label(logo_frame, image=self.logo_img, bg=COLOR_BLANCO).pack(anchor="center")
            except Exception as e:
                from vim_logger import get_logger
                get_logger("seguridad.login").warning(f"Error cargando logo: {e}")
                tk.Label(logo_frame, text="VIM ERP", fg=COLOR_PRIMARIO,
                         font=("Segoe UI", escalar_fuente(32, maximo=40), "bold"), bg=COLOR_BLANCO).pack()
        else:
            tk.Label(logo_frame, text="VIM ERP", fg=COLOR_PRIMARIO,
                     font=("Segoe UI", escalar_fuente(32, maximo=40), "bold"), bg=COLOR_BLANCO).pack()

        # Card de Login — centrada con pack en lugar de place
        frame_card = tk.Frame(main, bg=COLOR_BLANCO, bd=0)
        frame_card.pack(fill="x", padx=escalar(55), pady=(escalar(28), 0))

        tk.Label(frame_card, text="INICIO DE SESIÓN", font=("Segoe UI", escalar_fuente(12), "bold"), bg=COLOR_BLANCO, fg="#555").pack(pady=(0, 25))

        tk.Label(frame_card, text="Nombre de Usuario", font=("Segoe UI", escalar_fuente(9)), bg=COLOR_BLANCO, fg="#666").pack(anchor="w")
        self.users_list = self.obtener_usuarios_activos()
        self.cmb_user = ttk.Combobox(frame_card, values=self.users_list, font=("Segoe UI", escalar_fuente(11)), state="readonly")
        self.cmb_user.pack(fill="x", pady=(5, 15), ipady=4)
        if self.users_list:
            self.cmb_user.set(self.users_list[0])
        
        tk.Label(frame_card, text="Contraseña", font=("Segoe UI", escalar_fuente(9)), bg=COLOR_BLANCO, fg="#666").pack(anchor="w")
        self.ent_pass = tk.Entry(frame_card, font=("Segoe UI", escalar_fuente(11)), show="*")
        self.ent_pass.pack(fill="x", pady=(5, 25), ipady=6)

        self.btn_login = tk.Button(
            frame_card, text="INGRESAR AL SISTEMA", bg=COLOR_PRIMARIO, fg=COLOR_BLANCO,
            font=("Segoe UI", escalar_fuente(10), "bold"), relief="flat", cursor="hand2",
            activebackground=COLOR_SECUNDARIO, activeforeground=COLOR_BLANCO,
            command=self.intentar_login
        )
        self.btn_login.pack(fill="x", ipady=10)

        self.btn_olvide = tk.Button(
            frame_card, text="¿Olvidaste tu contraseña?", bg=COLOR_BLANCO, fg="#666",
            font=("Segoe UI", escalar_fuente(9), "underline"), relief="flat", cursor="hand2",
            activeforeground=COLOR_PRIMARIO, activebackground=COLOR_BLANCO,
            command=self.abrir_recuperacion
        )
        self.btn_olvide.pack(pady=(10, 0))

        # ── Primer inicio: mostrar la clave temporal del admin ──
        # Sin esto, la clave aleatoria generada por el seed solo se revelaba
        # DESPUÉS de iniciar sesión: imposible entrar en una instalación nueva.
        temp_pass = self._obtener_clave_temporal()
        if temp_pass:
            aviso = tk.Frame(main, bg="#fffbeb", highlightbackground="#fde68a", highlightthickness=1)
            aviso.pack(fill="x", padx=escalar(55), pady=(14, 0))
            tk.Label(
                aviso, text="🔑 PRIMER INICIO",
                font=("Segoe UI", escalar_fuente(8), "bold"), bg="#fffbeb", fg="#92400e"
            ).pack(pady=(8, 0))
            tk.Label(
                aviso,
                text=f"Usuario: admin    Clave temporal: {temp_pass}",
                font=("Segoe UI", escalar_fuente(11), "bold"), bg="#fffbeb", fg="#92400e"
            ).pack()
            tk.Label(
                aviso,
                text="Al entrar se te pedirá configurar tu pregunta de seguridad.\n"
                     "Luego cambia esta clave en el módulo Usuarios.",
                font=("Segoe UI", escalar_fuente(8)), bg="#fffbeb", fg="#a16207", justify="center"
            ).pack(pady=(2, 8))

        # Versión al fondo — pack side=bottom en vez de place
        tk.Label(main, text="v1.0 Professional Edition", font=("Segoe UI", escalar_fuente(8)),
                 bg=COLOR_BLANCO, fg="#999").pack(side="bottom", pady=(escalar(24), escalar(28)))

        # Eventos
        self.top.bind("<Return>", lambda e: self.intentar_login())
        self.ent_pass.focus_set()

    @staticmethod
    def _obtener_clave_temporal():
        """Clave temporal del primer inicio, o None si ya fue usada/borrada."""
        try:
            with session_db() as conn:
                row = conn.execute(
                    "SELECT valor FROM configuracion WHERE clave = 'admin_temp_password'"
                ).fetchone()
                return row[0] if row else None
        except Exception:
            return None

    def abrir_recuperacion(self):
        from modulos.seguridad.recuperacion_ui import ModalRecuperarClave
        ModalRecuperarClave(self.top)

    def obtener_usuarios_activos(self):
        try:
            with session_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT username FROM usuarios WHERE activo = 1 ORDER BY username")
                return [r[0] for r in cursor.fetchall()]
        except Exception as e:
            from vim_logger import get_logger
            get_logger("seguridad.login").error(f"Error cargando usuarios: {e}")
            return ["admin"]

    def intentar_login(self, event=None):
        username = self.cmb_user.get().strip()
        password = self.ent_pass.get()
        
        if not username or not password:
            messagebox.showwarning("Campos Vacíos", "Por favor ingrese su usuario y contraseña.")
            return

        if limiter.is_locked_out(username):
            messagebox.showerror(
                "Acceso Bloqueado",
                "Demasiados intentos fallidos.\n\n"
                "La cuenta está bloqueada por 5 minutos.\n"
                "Espere e intente nuevamente."
            )
            return

        usuario = autenticar_usuario(username, password)
        if usuario:
            Sesion.iniciar(usuario)
            self.top.destroy()
            self.on_success()
        else:
            remaining = limiter.remaining_attempts(username)
            if remaining == 0:
                messagebox.showerror(
                    "Acceso Bloqueado",
                    "Demasiados intentos fallidos.\n\n"
                    "La cuenta está bloqueada por 5 minutos.\n"
                    "Espere e intente nuevamente."
                )
            else:
                messagebox.showerror(
                    "Error de Acceso",
                    f"Usuario o contraseña incorrectos.\n\n"
                    f"Intentos restantes: {remaining} de 5."
                )
            self.ent_pass.delete(0, tk.END)
            self.ent_pass.focus_set()
