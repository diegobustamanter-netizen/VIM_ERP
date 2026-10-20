import tkinter as tk
from tkinter import ttk, messagebox
from config import COLOR_PRIMARIO, COLOR_BLANCO, FUENTE_BOTON
from database.connection import session_db
from modulos.seguridad.auth import hash_password, verify_password
from modulos.utils_globales import centrar_ventana_mejorado, preparar_modal_scrollable
from modulos.seguridad.sesion import Sesion
from ui_scale import escalar_fuente
from vim_logger import get_logger

PREGUNTAS_PREDEFINIDAS = [
    "¿Cuál es el nombre de tu primera mascota?",
    "¿En qué ciudad naciste?",
    "¿Cuál fue el modelo de tu primer auto?",
    "¿Cuál es tu color favorito?"
]

def verificar_y_forzar_configuracion_inicial(root):
    """Asistente único de puesta en marcha.

    Reúne en una sola ventana todo lo que hay que definir la primera vez:
    el tipo de negocio y la pregunta de seguridad del administrador.

    Antes eran dos ventanas separadas que se abrían casi a la vez: la de
    seguridad no bloqueaba, así que la de tipo de negocio aparecía encima y
    ambas se peleaban el foco. Ahora es un solo asistente por pasos, y sólo
    aparecen los pasos que realmente faltan.
    """
    from database.negocio import modo_configurado

    usuario = Sesion.get_usuario()
    es_admin = bool(usuario) and usuario.get("rol") == "administrador"

    pedir_negocio = not modo_configurado()
    pedir_seguridad = es_admin and not usuario.get("pregunta_seguridad")

    if not pedir_negocio and not pedir_seguridad:
        return

    modal = ModalOnboarding(
        root,
        usuario["id"] if usuario else None,
        pedir_negocio=pedir_negocio,
        pedir_seguridad=pedir_seguridad,
    )
    # Esperar de verdad: sin esto, lo que venga después se dibuja encima.
    root.wait_window(modal.top)


# Se mantiene el nombre anterior por si algo más lo llama
verificar_y_forzar_pregunta_seguridad = verificar_y_forzar_configuracion_inicial


class ModalOnboarding:
    """Asistente de configuración inicial, en pasos, en una sola ventana."""

    def __init__(self, parent, user_id, pedir_negocio=False, pedir_seguridad=True):
        self.parent = parent
        self.user_id = user_id

        # Sólo se incluyen los pasos que hacen falta
        self.pasos = ["bienvenida"]
        if pedir_negocio:
            self.pasos.append("negocio")
        if pedir_seguridad:
            self.pasos.append("seguridad")
        self.pasos.append("final")
        self._paso = 0

        self.top = tk.Toplevel(parent)
        self.top.title("Configuración inicial - VIM ERP")
        self.top.configure(bg=COLOR_BLANCO)
        self.top.transient(parent)
        self.top.protocol("WM_DELETE_WINDOW", self.bloquear_cierre)
        self.top.withdraw()

        # Contenedor principal con scroll adaptativo
        self.scroll_container = preparar_modal_scrollable(self.top, bg=COLOR_BLANCO)
        self.container = tk.Frame(self.scroll_container, bg=COLOR_BLANCO)
        self.container.pack(fill="both", expand=True)

        self._mostrar_paso()
        from ui_scale import escalar
        centrar_ventana_mejorado(self.top, escalar(620), escalar(600), relativo_a=parent)

        # grab_set toma el foco para esta ventana: nada más se puede tocar
        # hasta terminar. Va después de centrar, con la ventana ya visible.
        try:
            self.top.grab_set()
        except Exception:
            # SILENCIO DELIBERADO: si el gestor de ventanas no lo permite,
            # el asistente igual funciona, sólo que no bloquea el fondo.
            pass

    # ------------------------------------------------------------------
    # Recorrido de los pasos
    # ------------------------------------------------------------------

    def _mostrar_paso(self):
        nombre = self.pasos[self._paso]
        {
            "bienvenida": self.crear_fase1,
            "negocio": self.crear_fase_negocio,
            "seguridad": self.crear_fase2,
            "final": self.crear_fase3,
        }[nombre]()

    def _avanzar(self):
        self._paso += 1
        self._mostrar_paso()

    def _cerrar(self):
        try:
            self.top.grab_release()
        except Exception:
            pass  # SILENCIO DELIBERADO: puede no haberse tomado el grab
        self.top.destroy()

    def bloquear_cierre(self):
        messagebox.showwarning("Obligatorio", "Debes completar la configuración inicial antes de continuar.", parent=self.top)

    def limpiar_contenedor(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def crear_fase1(self):
        self.limpiar_contenedor()
        
        # Logo o título grande
        tk.Label(
            self.container, text="VIM ERP", font=("Segoe UI", escalar_fuente(28), "bold"),
            bg=COLOR_BLANCO, fg=COLOR_PRIMARIO
        ).pack(pady=(40, 10))

        tk.Label(
            self.container, 
            text="¡Bienvenido a tu nuevo sistema de gestión integral!",
            bg=COLOR_BLANCO, font=("Segoe UI", escalar_fuente(12), "bold")
        ).pack(pady=(0, 15))

        msg = (
            "Estamos felices de acompañar el crecimiento de tu negocio.\n\n"
            "Para garantizar la seguridad de tu información y asegurar que "
            "nunca pierdas el acceso a tu cuenta, necesitaremos realizar "
            "un par de pasos rápidos antes de comenzar."
        )
        tk.Label(
            self.container, text=msg, bg=COLOR_BLANCO, font=("Segoe UI", escalar_fuente(10)),
            justify="center", wraplength=400, fg="#555"
        ).pack(pady=(0, 30))

        btn = tk.Button(
            self.container, text="Comenzar Configuración ➔", font=FUENTE_BOTON,
            bg=COLOR_PRIMARIO, fg="white", relief="flat", cursor="hand2",
            command=self._avanzar
        )
        btn.pack(ipady=8, ipadx=10)

    # ------------------------------------------------------------------
    # Paso: tipo de negocio
    # ------------------------------------------------------------------

    def crear_fase_negocio(self):
        self.limpiar_contenedor()

        from database.negocio import MODO_PRODUCTOS, MODO_SERVICIOS, establecer_modo_negocio

        tk.Label(
            self.container, text="¿Qué tipo de negocio es?",
            font=("Segoe UI", escalar_fuente(16), "bold"),
            bg=COLOR_BLANCO, fg=COLOR_PRIMARIO
        ).pack(pady=(30, 10))

        tk.Label(
            self.container,
            text="Define si el sistema maneja stock e inventario.\n"
                 "Lo podés cambiar después en Configuración → Finanzas.",
            bg=COLOR_BLANCO, font=("Segoe UI", escalar_fuente(9)),
            justify="center", fg="#555"
        ).pack(pady=(0, 25), padx=20)

        fila = tk.Frame(self.container, bg=COLOR_BLANCO)
        fila.pack(pady=(0, 20))

        def elegir(modo):
            # convertir=True adapta los ítems de ejemplo de la instalación
            establecer_modo_negocio(modo, convertir=True)
            self._avanzar()

        def tarjeta(titulo, ejemplos, detalle, color, modo):
            marco = tk.Frame(fila, bg=COLOR_BLANCO, bd=1, relief="solid")
            marco.pack(side="left", padx=10)

            tk.Label(marco, text=titulo, font=("Segoe UI", escalar_fuente(13), "bold"),
                     fg=color, bg=COLOR_BLANCO).pack(pady=(16, 4), padx=20)
            tk.Label(marco, text=ejemplos, font=("Segoe UI", escalar_fuente(9)),
                     fg="#475569", bg=COLOR_BLANCO).pack(padx=20)
            tk.Label(marco, text=detalle, font=("Segoe UI", escalar_fuente(8), "italic"),
                     fg="#94a3b8", bg=COLOR_BLANCO, justify="center").pack(
                         padx=20, pady=(8, 12))
            tk.Button(
                marco, text="Elegir", bg=color, fg="white", relief="flat",
                font=("Segoe UI", escalar_fuente(10), "bold"), cursor="hand2",
                command=lambda: elegir(modo)
            ).pack(fill="x", padx=20, pady=(0, 18), ipady=5)

        tarjeta("🏷️  Productos", "Almacén, minimarket, tienda",
                "Maneja stock, inventario\ny proveedores", "#0ea5e9", MODO_PRODUCTOS)
        tarjeta("✂️  Servicios", "Peluquería, taller, consultora",
                "Sin stock ni inventario:\nse cobra por servicio prestado",
                "#10b981", MODO_SERVICIOS)

    def crear_fase2(self):
        self.limpiar_contenedor()

        tk.Label(
            self.container, text="Configuración de Seguridad", font=("Segoe UI", escalar_fuente(16), "bold"),
            bg=COLOR_BLANCO, fg=COLOR_PRIMARIO
        ).pack(pady=(30, 10))

        tk.Label(
            self.container, 
            text="Si alguna vez olvidas tu contraseña, esta será tu única forma de recuperarla.",
            bg=COLOR_BLANCO, font=("Segoe UI", escalar_fuente(9)), justify="center"
        ).pack(pady=(0, 25), padx=20)

        # Dropdown Preguntas
        tk.Label(self.container, text="Elige una pregunta secreta:", bg=COLOR_BLANCO, font=("Segoe UI", escalar_fuente(9), "bold")).pack(anchor="w", padx=40)
        self.cb_pregunta = ttk.Combobox(self.container, values=PREGUNTAS_PREDEFINIDAS, state="readonly", font=("Segoe UI", escalar_fuente(10)))
        self.cb_pregunta.current(0)
        self.cb_pregunta.pack(fill="x", padx=40, pady=(5, 15))

        # Inputs
        tk.Label(self.container, text="Palabra Clave (Respuesta):", bg=COLOR_BLANCO, font=("Segoe UI", escalar_fuente(9), "bold")).pack(anchor="w", padx=40)
        self.ent_respuesta1 = tk.Entry(self.container, show="*", font=("Segoe UI", escalar_fuente(11)), bd=1, relief="solid")
        self.ent_respuesta1.pack(fill="x", padx=40, pady=(5, 15))

        tk.Label(self.container, text="Repite tu Palabra Clave:", bg=COLOR_BLANCO, font=("Segoe UI", escalar_fuente(9), "bold")).pack(anchor="w", padx=40)
        self.ent_respuesta2 = tk.Entry(self.container, show="*", font=("Segoe UI", escalar_fuente(11)), bd=1, relief="solid")
        self.ent_respuesta2.pack(fill="x", padx=40, pady=(5, 25))

        # Botón
        btn = tk.Button(
            self.container, text="Guardar Seguridad", font=FUENTE_BOTON, bg="#28a745", fg="white",
            relief="flat", cursor="hand2", command=self.guardar_fase2
        )
        btn.pack(fill="x", padx=40, ipady=5)

    def guardar_fase2(self):
        preg = self.cb_pregunta.get()
        resp1 = self.ent_respuesta1.get().strip()
        resp2 = self.ent_respuesta2.get().strip()

        if not preg or not resp1 or not resp2:
            messagebox.showerror("Error", "Todos los campos son obligatorios.", parent=self.top)
            return

        if resp1 != resp2:
            messagebox.showerror("Error", "Las respuestas no coinciden. Escríbelas con cuidado.", parent=self.top)
            return

        try:
            r_hash = hash_password(resp1.lower())
            with session_db() as conn:
                conn.execute(
                    "UPDATE usuarios SET pregunta_seguridad = ?, respuesta_hash = ? WHERE id = ?",
                    (preg, r_hash, self.user_id)
                )
                conn.commit()
            
            # Actualizar la sesión en memoria
            Sesion.get_usuario()["pregunta_seguridad"] = preg

            self._avanzar()
        except Exception as e:
            get_logger("seguridad.recuperacion").exception("Falló al guardar en recuperación de clave")
            messagebox.showerror("Error", f"Error al guardar: {e}", parent=self.top)

    def crear_fase3(self):
        self.limpiar_contenedor()

        # La contraseña temporal sólo tiene sentido si en esta pasada se
        # configuró la seguridad del administrador. Si el asistente apareció
        # sólo para elegir el tipo de negocio, no corresponde mostrarla.
        hubo_seguridad = "seguridad" in self.pasos

        # Obtener contraseña temporal desde config
        temp_pass = None
        try:
            with session_db() as conn:
                row = conn.execute(
                    "SELECT valor FROM configuracion WHERE clave = 'admin_temp_password'"
                ).fetchone()
                if row:
                    temp_pass = row[0]
                    conn.execute(
                        "DELETE FROM configuracion WHERE clave = 'admin_temp_password'"
                    )
                    conn.commit()
        except Exception as e:
            # Si esto falla, la contraseña temporal queda guardada en texto
            # plano en la base. Tiene que quedar registrado.
            from vim_logger import get_logger
            get_logger("seguridad.recuperacion").error(
                f"No se pudo borrar la contraseña temporal del administrador: {e}"
            )

        tk.Label(
            self.container, text="✅", font=("Segoe UI", escalar_fuente(40)),
            bg=COLOR_BLANCO, fg="#28a745"
        ).pack(pady=(30, 10))

        titulo = "¡Todo listo!" if not hubo_seguridad else "¡Seguridad Configurada!"
        tk.Label(
            self.container, text=titulo, font=("Segoe UI", escalar_fuente(18), "bold"),
            bg=COLOR_BLANCO, fg=COLOR_PRIMARIO
        ).pack(pady=(0, 15))

        if hubo_seguridad and temp_pass:
            msg = (
                f"Tu contraseña temporal de administrador es:\n\n"
                f"{temp_pass}\n\n"
                "⚠️  Por seguridad, cámbiala inmediatamente desde el módulo de Usuarios.\n"
                "Esta contraseña NO se mostrará nuevamente."
            )
        else:
            msg = "Ya podés empezar a usar el sistema."

        tk.Label(
            self.container, text=msg, bg=COLOR_BLANCO, font=("Segoe UI", escalar_fuente(11)),
            justify="center", fg="#333", wraplength=420
        ).pack(pady=(0, 30))

        btn = tk.Button(
            self.container, text="¡Ir al Dashboard!", font=("Segoe UI", escalar_fuente(12), "bold"),
            bg=COLOR_PRIMARIO, fg="white", relief="flat", cursor="hand2",
            command=self._cerrar
        )
        btn.pack(ipady=10, ipadx=20)


class ModalRecuperarClave:
    def __init__(self, parent):
        self.parent = parent
        self.admin_user = None

        # Obtener admin
        try:
            with session_db(dict_rows=True) as conn:
                self.admin_user = conn.execute("SELECT * FROM usuarios WHERE rol = 'administrador' LIMIT 1").fetchone()
        except Exception as e:
            # Sin este dato la recuperación de contraseña no puede seguir, y
            # el usuario solo vería "no configurado" sin saber por qué.
            from vim_logger import get_logger
            get_logger("seguridad.recuperacion").error(
                f"No se pudo leer el usuario administrador: {e}"
            )

        if not self.admin_user or not self.admin_user.get("pregunta_seguridad"):
            messagebox.showerror("No Configurado", "El administrador no tiene configurada una pregunta de seguridad.", parent=parent)
            return

        self.top = tk.Toplevel(parent)
        self.top.title("Recuperar Contraseña")
        self.top.configure(bg=COLOR_BLANCO)
        self.top.attributes("-topmost", True)
        self.top.withdraw()

        body = preparar_modal_scrollable(self.top, bg=COLOR_BLANCO)

        tk.Label(
            body, text="🔒 Recuperación de Clave", font=("Segoe UI", escalar_fuente(14), "bold"),
            bg=COLOR_BLANCO, fg=COLOR_PRIMARIO
        ).pack(pady=(20, 10))

        tk.Label(
            body, text=f"Responde la pregunta secreta del Administrador:\n\n{self.admin_user['pregunta_seguridad']}",
            bg=COLOR_BLANCO, font=("Segoe UI", escalar_fuente(10)), justify="center", wraplength=350
        ).pack(pady=(0, 20), padx=20)

        tk.Label(body, text="Respuesta Secreta:", bg=COLOR_BLANCO, font=("Segoe UI", escalar_fuente(9), "bold")).pack(anchor="w", padx=30)
        self.ent_respuesta = tk.Entry(body, show="*", font=("Segoe UI", escalar_fuente(11)), bd=1, relief="solid")
        self.ent_respuesta.pack(fill="x", padx=30, pady=(5, 20))

        btn = tk.Button(
            body, text="Verificar Respuesta", font=FUENTE_BOTON, bg=COLOR_PRIMARIO, fg="white",
            relief="flat", cursor="hand2", command=self.verificar
        )
        btn.pack(fill="x", padx=30, pady=(0, 20), ipady=5)

        from ui_scale import escalar
        centrar_ventana_mejorado(self.top, escalar(480), escalar(400), relativo_a=parent)

    def verificar(self):
        resp = self.ent_respuesta.get().strip().lower()
        if not resp:
            messagebox.showerror("Error", "Ingresa una respuesta.", parent=self.top)
            return

        if verify_password(resp, self.admin_user["respuesta_hash"]):
            self.top.destroy()
            ModalNuevaClave(self.parent, self.admin_user["id"])
        else:
            messagebox.showerror("Error", "Respuesta incorrecta.", parent=self.top)


class ModalNuevaClave:
    def __init__(self, parent, user_id):
        self.parent = parent
        self.user_id = user_id

        self.top = tk.Toplevel(parent)
        self.top.title("Nueva Contraseña")
        self.top.configure(bg=COLOR_BLANCO)
        self.top.attributes("-topmost", True)
        self.top.withdraw()

        body = preparar_modal_scrollable(self.top, bg=COLOR_BLANCO)

        tk.Label(
            body, text="🔑 Crear Nueva Contraseña", font=("Segoe UI", escalar_fuente(14), "bold"),
            bg=COLOR_BLANCO, fg=COLOR_PRIMARIO
        ).pack(pady=(20, 15))

        tk.Label(body, text="Nueva Contraseña:", bg=COLOR_BLANCO, font=("Segoe UI", escalar_fuente(9), "bold")).pack(anchor="w", padx=30)
        self.ent_p1 = tk.Entry(body, show="*", font=("Segoe UI", escalar_fuente(11)), bd=1, relief="solid")
        self.ent_p1.pack(fill="x", padx=30, pady=(5, 15))

        tk.Label(body, text="Repetir Contraseña:", bg=COLOR_BLANCO, font=("Segoe UI", escalar_fuente(9), "bold")).pack(anchor="w", padx=30)
        self.ent_p2 = tk.Entry(body, show="*", font=("Segoe UI", escalar_fuente(11)), bd=1, relief="solid")
        self.ent_p2.pack(fill="x", padx=30, pady=(5, 20))

        btn = tk.Button(
            body, text="Guardar y Entrar", font=FUENTE_BOTON, bg="#28a745", fg="white",
            relief="flat", cursor="hand2", command=self.guardar
        )
        btn.pack(fill="x", padx=30, pady=(0, 20), ipady=5)

        from ui_scale import escalar
        centrar_ventana_mejorado(self.top, escalar(480), escalar(360), relativo_a=parent)

    def guardar(self):
        p1 = self.ent_p1.get().strip()
        p2 = self.ent_p2.get().strip()

        if not p1 or not p2:
            messagebox.showerror("Error", "Ingresa la contraseña.", parent=self.top)
            return

        if p1 != p2:
            messagebox.showerror("Error", "Las contraseñas no coinciden.", parent=self.top)
            return

        if len(p1) < 4:
            messagebox.showerror("Error", "La contraseña debe tener al menos 4 caracteres.", parent=self.top)
            return

        try:
            n_hash = hash_password(p1)
            with session_db() as conn:
                conn.execute("UPDATE usuarios SET password_hash = ? WHERE id = ?", (n_hash, self.user_id))
                conn.commit()
            
            messagebox.showinfo("Éxito", "Contraseña cambiada exitosamente. Ya puedes iniciar sesión.", parent=self.top)
            self.top.destroy()
        except Exception as e:
            get_logger("seguridad.recuperacion").exception("Falló al guardar en recuperación de clave")
            messagebox.showerror("Error", f"Error al guardar: {e}", parent=self.top)

