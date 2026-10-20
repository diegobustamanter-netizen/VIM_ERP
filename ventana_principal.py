import ctypes
import os

# ============================================================
# IDENTIDAD DE APLICACIÓN WINDOWS (debe ejecutarse ANTES de crear ventanas)
# Esto permite que Windows asocie el icono .ico con la app en la barra de tareas.
# ============================================================
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("vim.erp.desktop.1.0")
except Exception:
    from vim_logger import get_logger
    get_logger("app.startup").debug("No se pudo establecer AppUserModelID (no critico)", exc_info=True)

import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
from config import LOGO_PATH, ICO_PATH, COLOR_PRIMARIO, COLOR_SECUNDARIO, COLOR_BLANCO, COLOR_GRIS

from database import inicializar_db, obtener_caja_abierta, cerrar_caja, obtener_resumen_caja
from modulos.productos import abrir_modulo_productos
from modulos.pos.pos_main import abrir_modulo_pos
from modulos.caja import abrir_modulo_caja
from modulos.ventas_reportes import ModuloVentasReportes
from modulos.compras import compras_main
from modulos.configuracion import abrir_modulo_configuracion
from modulos.usuarios import abrir_modulo_usuarios
from modulos.seguridad.sesion import Sesion
from modulos.seguridad.login_ui import VentanaLogin
from modulos.seguridad.autorizacion_ui import solicitar_autorizacion_admin
from modulos.utils_globales import aplicar_barra_windows_azul, centrar_ventana_mejorado
from ui_scale import (
    preparar_dpi_awareness,
    inicializar_escala,
    registrar_autoescala,
    obtener_minimo_ventana,
    escalar,
    escalar_fuente,
)


# ============================================================
# UTILIDAD: ICONO PARA TODAS LAS VENTANAS
# ============================================================


def aplicar_icono(ventana):
    """Aplica el icono .ico a cualquier ventana (Tk o Toplevel).

    Usa iconbitmap(default=...) que:
    - Establece el icono en barra de título, Alt-Tab y taskbar
    - El parámetro 'default' hace que TODAS las ventanas hijas lo hereden
    - El .ico contiene múltiples tamaños y Windows elige el óptimo
    """
    try:
        if os.path.exists(ICO_PATH):
            ventana.iconbitmap(default=ICO_PATH)
    except Exception:
        from vim_logger import get_logger
        get_logger("ui.icono").debug("No se pudo aplicar icono a la ventana", exc_info=True)


# ============================================================
# ESTADO GLOBAL NAVEGACIÓN
# ============================================================

modulos_dashboard = []
indice_modulo_actual = 0
columnas_dashboard = 4
_app_shutdown = False  # Flag para prevenir callbacks durante cierre

root = None
frame_contenido = None
_frame_contenido_anterior = None  # Double-buffer: frame a destruir tras el swap
footer_frame = None
lbl_hora_footer = None
primer_inicio = True
vista_actual = None
panel_dashboard = None
dashboard_resize_after = None
reconstruccion_escala_after = None
hora_footer_after_id = None
modulo_pos_instancia = None      # Instancia viva del POS (para preservar el ticket)
_pos_ticket_pendiente = None     # Ticket a restaurar tras reconstruir por cambio de escala


# ============================================================
# UTILIDADES UI
# ============================================================

def centrar_ventana(ventana, ancho, alto):
    """Mantiene compatibilidad con código antiguo pero usando la lógica mejorada."""
    centrar_ventana_mejorado(ventana, ancho, alto)

def alternar_pantalla_completa(event=None):
    """Alterna entre pantalla completa real y modo maximizado."""
    is_fullscreen = root.attributes("-fullscreen")
    root.attributes("-fullscreen", not is_fullscreen)
    if is_fullscreen: # Si estábamos en fullscreen y salimos
        root.state("zoomed")
    return "break"


def limpiar_contenido():
    """Double-buffer: crea un frame nuevo vacío sin tocar el anterior.

    El frame anterior permanece visible mientras el módulo nuevo se construye
    en el frame oculto.  El swap ocurre en `mostrar_contenido()`.
    """
    global frame_contenido, _frame_contenido_anterior
    global modulos_dashboard, dashboard_resize_after, reconstruccion_escala_after

    if root is not None:
        if dashboard_resize_after:
            try:
                root.after_cancel(dashboard_resize_after)
            except Exception:
                pass  # after_cancel puede fallar si el timer ya se ejecuto
            dashboard_resize_after = None

        if reconstruccion_escala_after:
            try:
                root.after_cancel(reconstruccion_escala_after)
            except Exception:
                pass  # after_cancel puede fallar si el timer ya se ejecuto
            reconstruccion_escala_after = None

    modulos_dashboard = []

    if frame_contenido is None:
        return

    # Guardar el frame actual (sigue visible) para destruirlo en el swap
    _frame_contenido_anterior = frame_contenido

    # Crear frame nuevo — vacío y NO empaquetado (invisible)
    frame_contenido = tk.Frame(root, bg=COLOR_GRIS)


def mostrar_contenido():
    """Swap atómico: destruye el frame anterior y empaqueta el nuevo de golpe."""
    global _frame_contenido_anterior
    if frame_contenido is None or root is None:
        return

    # Destruir el frame anterior (si existe) y empaquetar el nuevo
    if _frame_contenido_anterior is not None:
        _frame_contenido_anterior.destroy()
        _frame_contenido_anterior = None

    frame_contenido.pack(side="top", expand=True, fill="both")


def programar_reconstruccion_por_escala():
    global reconstruccion_escala_after

    if root is None or vista_actual is None:
        return

    if reconstruccion_escala_after:
        try:
            root.after_cancel(reconstruccion_escala_after)
        except Exception:
            pass  # after_cancel puede fallar si el timer ya se ejecuto

    def _reconstruir():
        global reconstruccion_escala_after, _pos_ticket_pendiente
        reconstruccion_escala_after = None
        try:
            # Preservar el ticket del POS: reconstruir la vista crea un
            # ModuloPOS nuevo con ticket vacío. Sin esto, arrastrar la
            # ventana a otro monitor a mitad de una venta borraba el ticket.
            if (
                vista_actual is _abrir_pos
                and modulo_pos_instancia is not None
                and getattr(modulo_pos_instancia, "ticket", None)
            ):
                _pos_ticket_pendiente = list(modulo_pos_instancia.ticket)

            ancho_min, alto_min = obtener_minimo_ventana(root)
            root.minsize(ancho_min, alto_min)
            vista_actual()
        except Exception as e:
            from vim_logger import get_logger
            get_logger("ui.responsive").warning(f"No se pudo reconstruir la vista: {e}")

    reconstruccion_escala_after = root.after(350, _reconstruir)


def ajustar_minimo_ventana():
    if root is None:
        return
    ancho_min, alto_min = obtener_minimo_ventana(root)
    root.minsize(ancho_min, alto_min)


def fade_in(widget, alpha=0, speed=12, step=0.06):
    """Efecto de desvanecimiento rápido (~280ms) para primera carga."""
    try:
        if not widget.winfo_exists():
            return
        if alpha < 1:
            alpha = min(1.0, alpha + step)
            widget.attributes("-alpha", alpha)
            widget.after(speed, lambda: fade_in(widget, alpha, speed, step))
    except (tk.TclError, Exception):
        pass


class VentanaSplash:
    """Splash de carga que aparece antes del login."""
    def __init__(self, parent):
        import time as _time
        self.parent = parent
        self._start_time = _time.time()
        self.top = tk.Toplevel(parent)
        self.top.withdraw()  # Ocultar hasta posicionar
        self.top.overrideredirect(True)
        # Fondo blanco con un borde fino gris azulado: se ve limpio y el logo
        # (azul oscuro, transparente) resalta sin recuadros ni fondos oscuros.
        self.top.configure(bg="#d5dde8")
        aplicar_icono(self.top)

        from ui_scale import escalar
        contenedor = tk.Frame(self.top, bg=COLOR_BLANCO)
        contenedor.pack(fill="both", expand=True, padx=1, pady=1)

        logo_listo = False
        if os.path.exists(LOGO_PATH):
            try:
                img = Image.open(LOGO_PATH).convert("RGBA")
                # El PNG trae mucho margen transparente: se recorta al dibujo
                caja = img.getchannel("A").point(lambda v: 255 if v > 20 else 0).getbbox()
                if caja:
                    img = img.crop(caja)
                ancho_logo = escalar(340)
                alto_logo = max(1, int(img.height * ancho_logo / img.width))
                img = img.resize((ancho_logo, alto_logo), Image.Resampling.LANCZOS)
                self._logo_img = ImageTk.PhotoImage(img)  # referencia para que no se libere
                tk.Label(contenedor, image=self._logo_img, bg=COLOR_BLANCO).pack(pady=(escalar(52), 0))
                logo_listo = True
            except Exception:
                from vim_logger import get_logger
                get_logger("splash").exception("No se pudo cargar el logo del splash")
        if not logo_listo:
            tk.Label(
                contenedor, text="VIM ERP", bg=COLOR_BLANCO, fg=COLOR_PRIMARIO,
                font=("Segoe UI", escalar_fuente(30), "bold"),
            ).pack(pady=(escalar(52), 0))

        # Línea de acento corta y centrada
        tk.Frame(contenedor, bg=COLOR_PRIMARIO, height=3, width=escalar(56)).pack(pady=(escalar(26), escalar(16)))

        tk.Label(
            contenedor,
            text="Iniciando sistema...",
            bg=COLOR_BLANCO,
            fg="#475569",
            font=("Segoe UI", escalar_fuente(12), "bold"),
        ).pack()
        tk.Label(
            contenedor,
            text="Preparando el sistema",
            bg=COLOR_BLANCO,
            fg="#94a3b8",
            font=("Segoe UI", escalar_fuente(9)),
        ).pack(pady=(4, 0))

        # Centrar en el monitor donde está el parent, no solo el primario
        from ui_scale import escalar, obtener_metricas_monitor
        ancho_splash, alto_splash = escalar(480), escalar(280)
        self.top.update_idletasks()
        try:
            metricas = obtener_metricas_monitor(self.parent)
            sx = metricas["x"] + (metricas["width"] // 2) - (ancho_splash // 2)
            sy = metricas["y"] + (metricas["height"] // 2) - (alto_splash // 2)
        except Exception:
            sx = (self.top.winfo_screenwidth() // 2) - (ancho_splash // 2)
            sy = (self.top.winfo_screenheight() // 2) - (alto_splash // 2)
        self.top.geometry(f"{ancho_splash}x{alto_splash}+{max(0,sx)}+{max(0,sy)}")

    def mostrar(self):
        self.top.deiconify()
        self.top.lift()
        self.top.focus_force()
        self.top.update()  # update() completo para que se pinte de verdad

    def cerrar(self):
        """Cierra el splash, garantizando un mínimo de 1.2s de visibilidad."""
        import time as _time
        try:
            restante = 1.2 - (_time.time() - self._start_time)
            if restante > 0:
                self.top.after(int(restante * 1000), lambda: None)
                self.top.update()
                _time.sleep(max(0, restante - 0.05))
            if self.top.winfo_exists():
                self.top.destroy()
        except Exception:
            try:
                self.top.destroy()
            except Exception:
                pass  # ventana ya destruida, ignorar


def actualizar_hora_footer():
    global hora_footer_after_id
    try:
        if _app_shutdown:
            return
        # Verificar que tanto el root como el label existan antes de proceder
        if root is None or not root.winfo_exists():
            return
        if lbl_hora_footer is None or not lbl_hora_footer.winfo_exists():
            return

        from database.utils import ahora
        ahora_str = ahora("%d/%m/%Y  •  %H:%M")
        usuario_txt = f"Usuario: {Sesion.get_nombre()} ({Sesion.get_rol()})" if Sesion.get_usuario() else "No autenticado"
        lbl_hora_footer.config(text=f"VIM ERP v1.0 | {usuario_txt} | {ahora_str}")
        
        # Volver a programar solo si el widget sigue vivo
        hora_footer_after_id = lbl_hora_footer.after(60000, actualizar_hora_footer)
    except (tk.TclError, Exception):
        # Ignorar silenciosamente errores de Tcl al cerrar la aplicación
        pass


def crear_footer(parent):
    global lbl_hora_footer
    from config import FUENTE_FOOTER

    footer = tk.Frame(parent, bg=COLOR_PRIMARIO, height=max(38, escalar(40)))
    footer.pack(side="bottom", fill="x")
    footer.pack_propagate(False)

    lbl_hora_footer = tk.Label(
        footer,
        text="",
        fg=COLOR_BLANCO,
        bg=COLOR_PRIMARIO,
        font=FUENTE_FOOTER
    )
    lbl_hora_footer.pack(side="left", padx=15)

    tk.Label(
        footer,
        text="© 2026 VIM ERP",
        fg=COLOR_BLANCO,
        bg=COLOR_PRIMARIO,
        font=FUENTE_FOOTER
    ).pack(side="right", padx=15)

    actualizar_hora_footer()
    return footer




# ============================================================
# NAVEGACIÓN DASHBOARD
# ============================================================

def seleccionar_modulo(indice):
    global indice_modulo_actual

    if not modulos_dashboard:
        return

    indice_modulo_actual = indice % len(modulos_dashboard)

    for i, item in enumerate(modulos_dashboard):
        canvas = item["canvas"]
        rect = item["rect"]
        borde = item["borde"]
        linea = item["linea"]

        if i == indice_modulo_actual:
            canvas.itemconfig(rect, fill=COLOR_SECUNDARIO, outline=COLOR_SECUNDARIO)
            canvas.itemconfig(borde, outline=COLOR_BLANCO, width=2)
            canvas.itemconfig(linea, fill=COLOR_BLANCO, outline=COLOR_BLANCO)
        else:
            canvas.itemconfig(rect, fill=COLOR_PRIMARIO, outline=COLOR_PRIMARIO)
            canvas.itemconfig(borde, outline=COLOR_PRIMARIO, width=1)
            canvas.itemconfig(linea, fill=COLOR_SECUNDARIO, outline=COLOR_SECUNDARIO)


def mover_seleccion(event):

    if not modulos_dashboard:
        return "break"

    total = len(modulos_dashboard)
    keysym = event.keysym

    if keysym in ("Right", "KP_Right"):
        nuevo = (indice_modulo_actual + 1) % total
        seleccionar_modulo(nuevo)
    elif keysym in ("Left", "KP_Left"):
        nuevo = (indice_modulo_actual - 1) % total
        seleccionar_modulo(nuevo)
    elif keysym in ("Down", "KP_Down"):
        nuevo = (indice_modulo_actual + columnas_dashboard) % total
        seleccionar_modulo(nuevo)
    elif keysym in ("Up", "KP_Up"):
        nuevo = (indice_modulo_actual - columnas_dashboard) % total
        seleccionar_modulo(nuevo)

    return "break"


def abrir_modulo_seleccionado(event=None):
    if modulos_dashboard:
        modulos_dashboard[indice_modulo_actual]["comando"]()
    return "break"


def activar_navegacion_dashboard():
    # Asegurar el foco para capturar eventos de teclado
    root.focus_force()
    
    teclas_mover = ["<Right>", "<Left>", "<Down>", "<Up>", "<KP_Right>", "<KP_Left>", "<KP_Down>", "<KP_Up>"]
    for tecla in teclas_mover:
        root.bind(tecla, mover_seleccion)
        
    root.bind("<Return>", abrir_modulo_seleccionado)
    root.bind("<KP_Enter>", abrir_modulo_seleccionado)


def desactivar_navegacion_dashboard():
    teclas_mover = ["<Right>", "<Left>", "<Down>", "<Up>", "<KP_Right>", "<KP_Left>", "<KP_Down>", "<KP_Up>"]
    for tecla in teclas_mover:
        try:
            root.unbind(tecla)
        except Exception:
            pass  # unbind puede fallar si la tecla no estaba bindeada
            
    try:
        root.unbind("<Return>")
        root.unbind("<KP_Enter>")
    except Exception:
        pass  # unbind puede fallar si la tecla no estaba bindeada


# ============================================================
# APERTURA DE MÓDULOS
# ============================================================

def abrir_pos_desde_menu():
    verificar_permiso("VENTAS (POS)", _abrir_pos, "cajero", "pos")

def _abrir_pos():
    global vista_actual, modulo_pos_instancia, _pos_ticket_pendiente
    if not obtener_caja_abierta():
        messagebox.showwarning(
            "Caja Cerrada",
            "No puede acceder al Punto de Venta (POS) si la caja está cerrada.\n\n"
            "Por favor, realice la apertura de caja primero en el módulo 'Caja'."
        )
        return

    desactivar_navegacion_dashboard()
    limpiar_contenido()
    vista_actual = _abrir_pos
    modulo_pos_instancia = abrir_modulo_pos(root, frame_contenido, mostrar_menu_principal)

    # Restaurar ticket preservado tras una reconstrucción por cambio de escala
    if _pos_ticket_pendiente:
        try:
            modulo_pos_instancia.ticket = _pos_ticket_pendiente
            modulo_pos_instancia.refrescar_ticket()
        except Exception:
            from vim_logger import get_logger
            get_logger("ui.pos").warning("No se pudo restaurar el ticket tras reescalar", exc_info=True)
        _pos_ticket_pendiente = None

    mostrar_contenido()


def abrir_caja_desde_menu():
    verificar_permiso("CAJA", _abrir_caja, "cajero", "caja")

def _abrir_caja():
    global vista_actual
    desactivar_navegacion_dashboard()
    limpiar_contenido()
    vista_actual = _abrir_caja
    abrir_modulo_caja(root, frame_contenido, mostrar_menu_principal)
    mostrar_contenido()

# El módulo de productos ahora maneja el inventario de forma unificada
def abrir_productos_desde_menu():
    verificar_permiso("PRODUCTOS / INVENTARIO", _abrir_productos, "supervisor", "productos")

def _abrir_productos():
    global vista_actual
    desactivar_navegacion_dashboard()
    limpiar_contenido()
    vista_actual = _abrir_productos
    abrir_modulo_productos(root, frame_contenido, mostrar_menu_principal)
    mostrar_contenido()

def abrir_compras_desde_menu():
    verificar_permiso("COMPRAS Y PROVEEDORES", _abrir_compras, "supervisor", "compras")

def _abrir_compras():
    global vista_actual
    desactivar_navegacion_dashboard()
    limpiar_contenido()
    vista_actual = _abrir_compras
    compras_main.abrir_modulo(root, frame_contenido, mostrar_menu_principal)
    mostrar_contenido()

def abrir_ventas_desde_menu():
    verificar_permiso("REPORTES DE VENTAS", _abrir_ventas, "supervisor", "reportes")

def _abrir_ventas():
    global vista_actual
    desactivar_navegacion_dashboard()
    limpiar_contenido()
    # ModuloVentasReportes ya está importado en la cabecera
    vista_actual = _abrir_ventas
    ModuloVentasReportes(root, frame_contenido, mostrar_menu_principal)
    mostrar_contenido()


def abrir_configuracion_desde_menu():
    verificar_permiso("CONFIGURACIÓN", _abrir_configuracion, "administrador", "configuracion")

def _abrir_configuracion():
    global vista_actual
    desactivar_navegacion_dashboard()
    limpiar_contenido()
    vista_actual = _abrir_configuracion
    abrir_modulo_configuracion(root, frame_contenido, mostrar_menu_principal)
    mostrar_contenido()

def abrir_usuarios_desde_menu():
    verificar_permiso("GESTIÓN DE USUARIOS", _abrir_usuarios, "administrador", "usuarios")

def _abrir_usuarios():
    global vista_actual
    desactivar_navegacion_dashboard()
    limpiar_contenido()
    vista_actual = _abrir_usuarios
    abrir_modulo_usuarios(root, frame_contenido, mostrar_menu_principal)
    mostrar_contenido()

def abrir_web_externa():
    """Abre el sitio web externo en el navegador predeterminado."""
    import webbrowser
    url = "https://www.google.com"
    webbrowser.open(url)


def verificar_permiso(nombre_modulo, callback, nivel_requerido, modulo_slug=None):
    # Recargar permisos automáticamente antes de verificar
    Sesion.recargar_permisos()

    # 1. ¿Tiene permiso granular por módulo?
    # Si se proporciona modulo_slug, este check es el determinante.
    if modulo_slug:
        if Sesion.puede_acceder(modulo_slug):
            callback()
            return
        else:
            # Si el checkbox está apagado para este módulo, prohibimos el acceso
            # incluso si el rol del usuario es suficiente, cumpliendo el deseo del admin.
            if solicitar_autorizacion_admin(root, f"Acceder a {nombre_modulo}"):
                callback()
            else:
                root.focus_force()
            return

    # 2. Si NO hay modulo_slug, verificar nivel de rol jerárquico (comportamiento legacy)
    if Sesion.tiene_permiso(nivel_requerido):
        callback()
    else:
        if solicitar_autorizacion_admin(root, f"Acceder a {nombre_modulo}"):
            callback()
        else:
            root.focus_force()


# ============================================================
# BOTONES DASHBOARD
# ============================================================

def crear_boton_modulo(parent, texto, comando, indice):
    contenedor = tk.Frame(parent, bg=COLOR_GRIS)
    # Ajustado para que los botones sean más grandes pero no se corten en pantallas pequeñas
    ancho = max(230, escalar(260))
    alto = max(115, escalar(130))
    margen = max(5, escalar(5))
    sombra = max(10, escalar(10))
    linea_h = max(8, escalar(8))

    canvas = tk.Canvas(
        contenedor,
        width=ancho,
        height=alto,
        bg=COLOR_GRIS,
        highlightthickness=0,
        cursor="hand2",
        bd=0
    )
    canvas.pack()

    canvas.create_rectangle(
        sombra, sombra, ancho - 6, alto - 6,
        fill="#d7dbe0",
        outline="#d7dbe0"
    )

    rect = canvas.create_rectangle(
        margen, margen, ancho - 14, alto - 13,
        fill=COLOR_PRIMARIO,
        outline=COLOR_PRIMARIO
    )

    borde = canvas.create_rectangle(
        margen, margen, ancho - 14, alto - 13,
        outline=COLOR_PRIMARIO,
        width=1
    )

    linea = canvas.create_rectangle(
        margen, margen, ancho - 14, margen + linea_h,
        fill=COLOR_SECUNDARIO,
        outline=COLOR_SECUNDARIO
    )

    canvas.create_text(
        ancho // 2,
        alto // 2,
        text=texto,
        fill=COLOR_BLANCO,
        font=("Segoe UI", max(10, escalar(12)), "bold"),
        width=ancho - 40,
        justify="center"
    )

    def hover(_event):
        seleccionar_modulo(indice)

    def leave(_event):
        pass

    def click(_event):
        seleccionar_modulo(indice)
        comando()

    canvas.bind("<Enter>", hover)
    canvas.bind("<Leave>", leave)
    canvas.bind("<Button-1>", click)

    modulos_dashboard.append({
        "contenedor": contenedor,
        "canvas": canvas,
        "rect": rect,
        "borde": borde,
        "linea": linea,
        "comando": comando
    })

    return contenedor


def reacomodar_dashboard(event=None):
    global columnas_dashboard, dashboard_resize_after

    if not modulos_dashboard or root is None:
        return

    if event is not None:
        if dashboard_resize_after:
            try:
                root.after_cancel(dashboard_resize_after)
            except Exception:
                pass
        dashboard_resize_after = root.after(60, reacomodar_dashboard)
        return

    # Preferencia: 4 botones arriba y 4 abajo. Pero si la ventana es más
    # angosta que lo que ocupan 4 botones (min 230px c/u + márgenes),
    # bajar a 2 columnas para que no se corten los botones laterales.
    ancho_boton = max(230, escalar(260))
    margen = max(8, escalar(14))
    ancho_necesario_4 = 4 * (ancho_boton + 2 * margen) + escalar(40)
    try:
        ancho_disponible = root.winfo_width()
        if ancho_disponible <= 1:  # Ventana aún no mapeada: no decidir todavía
            ancho_disponible = ancho_necesario_4
    except Exception:
        ancho_disponible = ancho_necesario_4
    columnas_dashboard = 4 if ancho_disponible >= ancho_necesario_4 else 2

    for i, item in enumerate(modulos_dashboard):
        contenedor = item.get("contenedor")
        if not contenedor:
            continue
        contenedor.grid_configure(
            row=i // columnas_dashboard,
            column=i % columnas_dashboard,
            padx=max(8, escalar(14)),
            pady=max(8, escalar(14)),
        )

    seleccionar_modulo(indice_modulo_actual)


# ============================================================
# MENÚ PRINCIPAL
# ============================================================

def mostrar_menu_principal():
    global modulos_dashboard, indice_modulo_actual, primer_inicio, vista_actual, panel_dashboard
    global modulo_pos_instancia, _pos_ticket_pendiente
    from config import FUENTE_TITULO

    vista_actual = mostrar_menu_principal
    modulo_pos_instancia = None   # El POS ya no está activo
    _pos_ticket_pendiente = None
    ajustar_minimo_ventana()
    if primer_inicio:
        root.attributes("-alpha", 0) # 1. Hacer invisible
        root.deiconify() # 2. Mostrar la ventana pero es transparente
        root.state("zoomed") # 3. Maximizar mientras no se ve
        aplicar_icono(root)  # Re-aplicar icono tras state("zoomed")
        root.update_idletasks() # 4. Forzar el redibujado
    else:
        root.state("zoomed") # En uso normal, simplemente asegurar maximizado
        aplicar_icono(root)  # Re-aplicar icono tras state("zoomed")
        root.deiconify()

    # Re-aplicar icono con delay: Windows puede resetear el icono de la taskbar
    # durante la transición de ventanas (Toplevel login → root maximizado).
    # Un after() garantiza que se aplique DESPUÉS de que el WM termine.
    root.after(150, lambda: aplicar_icono(root))
    limpiar_contenido()
    desactivar_navegacion_dashboard()
    modulos_dashboard = []
    indice_modulo_actual = 0

    # El header y un espaciador inferior se reparten el alto libre:
    # así el logo queda centrado entre la barra superior y los botones,
    # y los botones quedan al medio del espacio restante.
    header_menu = tk.Frame(frame_contenido, bg=COLOR_GRIS)
    header_menu.pack(fill="both", expand=True)

    if os.path.exists(LOGO_PATH):
        try:
            if getattr(root, "logo_cache", None) is None:
                from modulos.utils_globales import cargar_logo_recortado
                img = cargar_logo_recortado(LOGO_PATH, escalar(340), escalar(110))
                root.logo_cache = ImageTk.PhotoImage(img)

            tk.Label(header_menu, image=root.logo_cache, bg=COLOR_GRIS).pack(
                expand=True, pady=escalar(16)
            )
        except Exception as e:
            from vim_logger import get_logger
            get_logger("ui.dashboard").warning(f"Error cargando imagen: {e}")
            tk.Label(
                header_menu,
                text="VIM ERP",
                font=FUENTE_TITULO,
                fg=COLOR_PRIMARIO,
                bg=COLOR_GRIS
            ).pack(pady=(30, 20))
    else:
        tk.Label(
            header_menu,
            text="VIM ERP",
            font=FUENTE_TITULO,
            fg=COLOR_PRIMARIO,
            bg=COLOR_GRIS
        ).pack(pady=(30, 20))

    panel_wrapper = tk.Frame(frame_contenido, bg=COLOR_GRIS)
    panel_wrapper.pack()

    espaciador_inferior = tk.Frame(frame_contenido, bg=COLOR_GRIS)
    espaciador_inferior.pack(fill="both", expand=True)

    panel = tk.Frame(panel_wrapper, bg=COLOR_GRIS)
    panel.pack()
    panel_dashboard = panel
    panel.bind("<Configure>", reacomodar_dashboard, add="+")

    from database.negocio import es_negocio_de_servicios
    etiqueta_catalogo = "✂️ Servicios" if es_negocio_de_servicios() else "🏷️ Productos"

    modulos = [
        ("🛒 Punto de Venta (POS)", abrir_pos_desde_menu),
        (etiqueta_catalogo, abrir_productos_desde_menu),
        ("📊 Ventas / Reportes", abrir_ventas_desde_menu),
        ("🛍️ Administración", abrir_compras_desde_menu),
        ("💰 Caja", abrir_caja_desde_menu),
        ("👨‍💼 Usuarios", abrir_usuarios_desde_menu),
        ("⚙️ Configuración", abrir_configuracion_desde_menu),
        ("🌐 VIM ERP", abrir_web_externa),
    ]

    for i, (texto, comando) in enumerate(modulos):
        fila = i // columnas_dashboard
        col = i % columnas_dashboard
        btn = crear_boton_modulo(panel, texto, comando, i)
        btn.grid(row=fila, column=col, padx=max(8, escalar(14)), pady=max(8, escalar(14)))

    activar_navegacion_dashboard()
    mostrar_contenido()
    seleccionar_modulo(0)
    root.focus_force()
    if primer_inicio:
        fade_in(root, speed=12, step=0.06)
        
        # Asistente único de puesta en marcha: tipo de negocio y pregunta de
        # seguridad en una sola ventana. Antes eran dos modales que se abrían
        # casi a la vez y se peleaban el foco.
        try:
            from modulos.seguridad.recuperacion_ui import verificar_y_forzar_configuracion_inicial
            verificar_y_forzar_configuracion_inicial(root)
        except Exception as e:
            from vim_logger import get_logger
            get_logger("configuracion.inicial").error(
                f"Falló el asistente de configuración inicial: {e}", exc_info=True
            )

        primer_inicio = False

    # Iniciar monitoreo de timeout de sesión.
    # Nota: no se bindea <Motion> — dispararía un callback de Python por cada
    # pixel de movimiento del mouse. Teclas y clics bastan como actividad.
    root.bind("<Key>", lambda e: Sesion.registrar_actividad(), add="+")
    root.bind("<Button>", lambda e: Sesion.registrar_actividad(), add="+")
    _verificar_timeout_sesion()


_verificar_timeout_after_id = None

def _verificar_timeout_sesion():
    """Verifica periódicamente si la sesión expiró por inactividad.

    Si el timeout está desactivado (Sesion._timeout_segundos = 0) ni siquiera
    se reprograma el chequeo: no tiene sentido despertar cada minuto.
    """
    global _verificar_timeout_after_id
    if _app_shutdown or root is None:
        return
    if not Sesion.timeout_activo():
        _verificar_timeout_after_id = None
        return
    if Sesion.sesion_expirada():
        messagebox.showwarning(
            "Sesión Expirada",
            "Tu sesión ha expirado por inactividad.\nLa aplicación se cerrará.",
            parent=root
        )
        # Usar la misma ruta de salida que el botón X: ofrece cierre de caja,
        # cancela timers y usa quit() (destroy() directo provocaba errores Tcl).
        confirmar_salida()
        return
    _verificar_timeout_after_id = root.after(60000, _verificar_timeout_sesion)


def _ticket_pos_en_curso():
    """Devuelve las líneas del ticket del POS si hay una venta a medio armar.

    Contempla los dos lugares donde puede estar viva: el módulo POS abierto y
    el respaldo temporal que se usa al reconstruir la vista por cambio de
    escala o de monitor.
    """
    if modulo_pos_instancia is not None:
        lineas = getattr(modulo_pos_instancia, "ticket", None)
        if lineas:
            return lineas
    if _pos_ticket_pendiente:
        return _pos_ticket_pendiente
    return None


def confirmar_salida():
    """Verifica si hay caja abierta y ofrece cerrarla antes de salir."""
    global _app_shutdown

    # Antes que nada: avisar si hay una venta sin cobrar. Va primero para que,
    # si el usuario se arrepiente, la aplicación quede intacta (sin marcar
    # _app_shutdown ni cancelar los timers).
    lineas_ticket = _ticket_pos_en_curso()
    if lineas_ticket:
        try:
            total_ticket = sum(float(l.get("subtotal") or 0) for l in lineas_ticket)
            total_txt = f"$ {total_ticket:,.0f}".replace(",", ".")
        except Exception:
            total_txt = "monto no disponible"

        if not messagebox.askyesno(
            "Venta sin cobrar",
            f"Hay una venta a medio armar en el Punto de Venta:\n\n"
            f"    {len(lineas_ticket)} línea(s) por un total de {total_txt}\n\n"
            "Si cerrás el programa ese ticket se pierde.\n\n"
            "¿Deseas cerrar de todas formas?",
            default="no",
            icon="warning",
            parent=root
        ):
            return  # El usuario vuelve a su venta: no se cierra nada

    _app_shutdown = True  # Set flag to prevent further callbacks
    
    # Cancelar timers activos para evitar errores de Tcl en consola
    for timer_name in ["hora_footer_after_id", "dashboard_resize_after", "reconstruccion_escala_after", "_verificar_timeout_after_id"]:
        try:
            timer_id = globals().get(timer_name)
            if timer_id:
                root.after_cancel(timer_id)
        except Exception:
            pass

    try:
        caja = obtener_caja_abierta()
        if caja:
            if messagebox.askyesno(
                "Caja Abierta", 
                "Hay una sesión de caja abierta.\n\n"
                "¿Desea realizar el CIERRE DE CAJA automáticamente antes de salir?",
                parent=root
            ):
                resumen = obtener_resumen_caja(caja["id"])
                if resumen:
                    monto_cierre = resumen.get("efectivo_esperado", 0)
                    cerrar_caja(caja["id"], monto_cierre, Sesion.get_usuario_id())
                    messagebox.showinfo("Caja Cerrada", f"La caja se ha cerrado con el monto esperado: ${monto_cierre:,.0f}".replace(",", "."))
    except Exception as e:
        from vim_logger import get_logger
        get_logger("app").error(f"Error al intentar cerrar caja al salir: {e}")
    
    # Use quit() instead of destroy() to avoid Tcl command deletion errors
    # quit() exits the event loop cleanly without trying to recursively destroy widgets
    try:
        root.quit()
    except Exception as e:
        from vim_logger import get_logger
        get_logger("app").error(f"Error during root.quit(): {e}")
        import sys
        sys.exit(0)




# ============================================================
# INICIO DE LA APLICACIÓN
# ============================================================

if __name__ == "__main__":
    # SetCurrentProcessExplicitAppUserModelID ya se ejecutó al nivel de módulo

    preparar_dpi_awareness()
    root = tk.Tk()
    root.withdraw()  # Ocultar INMEDIATAMENTE para evitar cuadro blanco
    root.attributes("-alpha", 0)  # Doble seguro: totalmente transparente
    root.title("VIM ERP - Sistema de Gestión")
    root.configure(bg=COLOR_GRIS)

    # Establecer el icono de la ventana (barra de titulo, taskbar, Alt-Tab)
    aplicar_icono(root)

    # Inicializar el sistema de escalado ANTES de construir cualquier interfaz.
    # Detecta resolución + DPI real del monitor para ajustar los tamaños de paneles.
    inicializar_escala(root)
    registrar_autoescala(root, programar_reconstruccion_por_escala)

    # NO llamar root.state("zoomed") aquí — en Windows deshace el withdraw()
    # y provoca el cuadro blanco. mostrar_menu_principal() ya lo aplica
    # con alpha=0 + fade_in para una transición limpia.

    # Atajos opcionales para pantalla completa
    root.bind("<F11>", alternar_pantalla_completa)
    root.bind("<Escape>", lambda e: root.attributes("-fullscreen", False) or root.state("zoomed"))
    ajustar_minimo_ventana()

    # ── Splash de carga ──────────────────────────────────────
    # El splash aparece mientras se prepara todo (DB, footer, login)
    splash = VentanaSplash(root)
    splash.mostrar()

    # Inicializar base de datos mientras el splash es visible
    inicializar_db()

    # Orden de empaquetado: El footer abajo primero, luego el contenido arriba
    footer_frame = crear_footer(root)

    frame_contenido = tk.Frame(root, bg=COLOR_GRIS)
    frame_contenido.pack(side="top", expand=True, fill="both")

    # --- Estilización Global de Cuadros de Texto (Entries) ---
    root.option_add('*Entry.relief', 'flat')
    root.option_add('*Entry.highlightThickness', 1)
    root.option_add('*Entry.highlightBackground', '#cbd5e1')
    root.option_add('*Entry.highlightColor', COLOR_PRIMARIO)
    root.option_add('*Entry.font', ('Segoe UI', escalar_fuente(10)))

    # Efecto de foco global para todos los Entry del sistema
    def on_global_focus_in(event):
        try:
            if isinstance(event.widget, tk.Entry):
                event.widget.config(highlightthickness=1, highlightbackground=COLOR_PRIMARIO, highlightcolor=COLOR_PRIMARIO)
        except Exception: pass

    def on_global_focus_out(event):
        try:
            if isinstance(event.widget, tk.Entry):
                event.widget.config(highlightthickness=1, highlightbackground='#cbd5e1', highlightcolor='#cbd5e1')
        except Exception: pass

    root.bind_class("Entry", "<FocusIn>", on_global_focus_in)
    root.bind_class("Entry", "<FocusOut>", on_global_focus_out)

    # Construir el login MIENTRAS el splash sigue visible
    # VentanaLogin hace withdraw+deiconify internamente, así que
    # primero lo creamos y luego cerramos el splash para una
    # transición splash → login sin cuadro blanco intermedio.
    login = VentanaLogin(root, mostrar_menu_principal)

    # Cerrar splash DESPUÉS de que el login ya esté listo y visible
    splash.cerrar()

    aplicar_barra_windows_azul(root, COLOR_PRIMARIO, COLOR_BLANCO)

    root.protocol("WM_DELETE_WINDOW", confirmar_salida)
    # El fade_in se activará al entrar al menú principal tras el login
    root.mainloop()
