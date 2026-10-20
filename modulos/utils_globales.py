import tkinter as tk
from tkinter import ttk
import os
import ctypes
from config import COLOR_PRIMARIO

def configurar_focus_entry(entry, color_normal="#cbd5e1"):
    """
    Agrega resaltado al recibir el foco en un Entry para un look moderno.
    """
    def on_focus_in(e):
        entry.config(highlightthickness=1, highlightbackground=COLOR_PRIMARIO, highlightcolor=COLOR_PRIMARIO)
    def on_focus_out(e):
        entry.config(highlightthickness=1, highlightbackground=color_normal, highlightcolor=color_normal)
    
    entry.config(highlightthickness=1, highlightbackground=color_normal, highlightcolor=color_normal, relief="flat")
    entry.bind("<FocusIn>", on_focus_in)
    entry.bind("<FocusOut>", on_focus_out)

def limpiar_formato_numerico(texto):
    """
    Elimina los puntos de miles para conversión numérica.
    Asume que el punto (.) es separador de miles y la coma (,) es decimal.
    """
    if not texto:
        return "0"
    texto = str(texto).strip()
    return texto.replace(".", "").replace(",", ".")

def formatear_para_edicion(valor):
    """
    Convierte un valor numérico (float/int) de la DB a un string localizado para Entry.
    Ejemplo: 1500.5 -> "1.500,5"
    """
    if valor is None:
        return ""
    try:
        f_valor = float(valor)
        if f_valor == 0:
            return "0"
        
        # Formatear con miles (.) y decimales (,)
        # 1. Redondear para evitar precision issues (ej. 1.234,8899999999)
        # 2. Convertir a string con comas para miles y puntos para decimales
        s_valor = f"{round(f_valor, 8):,.8f}".rstrip('0').rstrip('.')
        
        # 3. Intercambiar separadores para el formato local:
        temp = s_valor.replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")
        return temp
    except Exception:
        return str(valor)

def formatear_con_miles(event):
    """
    Formatea el contenido de un Entry con separadores de miles (.)
    mientras se escribe, manteniendo la posición del cursor.
    """
    widget = event.widget
    if not isinstance(widget, tk.Entry):
        return

    # Obtener contenido actual y posición del cursor
    contenido_original = widget.get()
    posicion_cursor = widget.index(tk.INSERT)
    
    # Si está vacío, no hacer nada
    if not contenido_original:
        return

    # Guardar cuántos caracteres (no puntos) hay antes del cursor
    # para reposicionarlo correctamente después
    texto_antes_cursor = contenido_original[:posicion_cursor]
    caracteres_antes_cursor = len(texto_antes_cursor.replace(".", ""))

    # Limpiar todo lo que no sea número (o coma para decimales si fuera necesario, 
    # pero el usuario pidió puntos de miles)
    # Solo permitimos números para el formateo de miles básico
    solo_numeros = contenido_original.replace(".", "")
    
    # Verificar si es un número válido (evitar letras)
    if not solo_numeros.isdigit() and solo_numeros != "":
        # Si hay caracteres no numéricos, podríamos querer filtrarlos o dejarlos
        # Para este ERP, asumimos que son campos puramente numéricos
        pass

    try:
        if solo_numeros == "":
            nuevo_contenido = ""
        else:
            # Formatear con puntos de miles
            valor_int = int(solo_numeros)
            nuevo_contenido = f"{valor_int:,}".replace(",", ".")
    except ValueError:
        # Si no se puede convertir a int (ej. caracteres extraños), 
        # mantenemos lo que hay o limpiamos
        return

    # Solo actualizar si el contenido cambió para evitar recursión/parpadeo innecesario
    if nuevo_contenido != contenido_original:
        widget.delete(0, tk.END)
        widget.insert(0, nuevo_contenido)
        
        # Calcular nueva posición del cursor
        # Buscamos la posición donde el conteo de "caracteres no punto" sea el mismo
        nueva_posicion = 0
        conteo_caracteres = 0
        for i, char in enumerate(nuevo_contenido):
            if conteo_caracteres == caracteres_antes_cursor:
                break
            if char != ".":
                conteo_caracteres += 1
            nueva_posicion = i + 1
            
        widget.icursor(nueva_posicion)

def formatear_rut(event):
    """
    Formatea el contenido de un Entry como RUT chileno (12345678-9) 
    mientras se escribe.
    """
    if getattr(event, 'keysym', '') in ("BackSpace", "Delete", "Left", "Right", "Up", "Down", "Tab"):
        return

    widget = getattr(event, 'widget', None)
    if not isinstance(widget, tk.Entry):
        return

    valor = widget.get()
    
    # Limpiar lo que no es alfanumerico
    texto = "".join([c.upper() for c in valor if c.isalnum()])
    
    if len(texto) > 1:
        nuevo_contenido = f"{texto[:-1]}-{texto[-1]}"
    else:
        nuevo_contenido = texto
        
    if nuevo_contenido != valor:
        widget.delete(0, tk.END)
        widget.insert(0, nuevo_contenido)
        widget.icursor(tk.END)

def hex_a_colorref(hex_color):
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return b << 16 | g << 8 | r

def aplicar_barra_windows_azul(ventana, color_fondo=COLOR_PRIMARIO, color_texto="#ffffff"):
    """Aplica el color institucional a la barra de título de Windows (Win11/10)."""
    if os.name != "nt":
        return

    try:
        ventana.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(ventana.winfo_id())

        DWMWA_BORDER_COLOR = 34
        DWMWA_CAPTION_COLOR = 35
        DWMWA_TEXT_COLOR = 36

        color_caption = ctypes.c_int(hex_a_colorref(color_fondo))
        color_text = ctypes.c_int(hex_a_colorref(color_texto))
        color_border = ctypes.c_int(hex_a_colorref(color_fondo))

        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_CAPTION_COLOR,
            ctypes.byref(color_caption),
            ctypes.sizeof(color_caption)
        )

        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_TEXT_COLOR,
            ctypes.byref(color_text),
            ctypes.sizeof(color_text)
        )

        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_BORDER_COLOR,
            ctypes.byref(color_border),
            ctypes.sizeof(color_border)
        )
    except Exception as e:
        print(f"No se pudo aplicar color a la barra de Windows: {e}")

def centrar_ventana_mejorado(ventana, ancho, alto, relativo_a=None, mostrar=True):
    """
    Centra una ventana en la pantalla o relativa a otra ventana,
    evitando el parpadeo de 'salto' de posición inicial.

    Soporte multi-monitor: si se pasa relativo_a, centra sobre esa ventana.
    Si no, detecta el monitor donde está el parent (ventana.master) y centra allí.
    """
    from ui_scale import obtener_metricas_monitor

    ventana.withdraw() # Ocultar inmediatamente
    ventana.update_idletasks()

    # Metricas del monitor de referencia (donde esta el parent o relativo_a).
    # Se usan SIEMPRE para: (a) recortar el tamano del modal al area util
    # y (b) mantener la ventana dentro del monitor correcto (multi-monitor).
    metricas = None
    try:
        metricas = obtener_metricas_monitor(relativo_a or ventana.master)
    except Exception:
        # SILENCIO DELIBERADO: falla en equipos sin la API multi-monitor de
        # Windows. Hay un fallback con winfo_screenwidth más abajo, así que
        # el modal se ubica igual. Loguearlo repetiría el mismo aviso cada
        # vez que se abre una ventana.
        pass

    if metricas:
        mon_x, mon_y = metricas["x"], metricas["y"]
        mon_w, mon_h = metricas["width"], metricas["height"]
    else:
        mon_x, mon_y = 0, 0
        mon_w = ventana.winfo_screenwidth()
        mon_h = ventana.winfo_screenheight()

    # Recorte al area util del monitor (aplica a TODOS los modales,
    # con o sin relativo_a). Antes solo se recortaba sin relativo_a,
    # y en pantallas chicas o DPI alto los modales quedaban cortados.
    ancho = min(ancho, max(320, mon_w - 80))
    alto = min(alto, max(260, mon_h - 80))

    if relativo_a:
        # Centrar relativo a otra ventana (ej. modal sobre principal)
        try:
            relativo_a.update_idletasks()
            rx = relativo_a.winfo_rootx()
            ry = relativo_a.winfo_rooty()
            rw = relativo_a.winfo_width()
            rh = relativo_a.winfo_height()

            x = rx + (rw // 2) - (ancho // 2)
            y = ry + (rh // 2) - (alto // 2)
        except Exception:
            x = mon_x + (mon_w // 2) - (ancho // 2)
            y = mon_y + (mon_h // 2) - (alto // 2)
    else:
        # Centrar en el monitor donde está el parent de la ventana
        x = mon_x + (mon_w // 2) - (ancho // 2)
        y = mon_y + (mon_h // 2) - (alto // 2)

    # Asegurar que la ventana quede dentro del area visible del MONITOR
    # de referencia (no forzar a >=0: los monitores secundarios a la
    # izquierda/arriba del principal tienen coordenadas negativas).
    x = max(mon_x, min(x, mon_x + mon_w - ancho))
    y = max(mon_y, min(y, mon_y + mon_h - alto))

    ventana.geometry(f"{ancho}x{alto}+{x}+{y}")
    if mostrar:
        ventana.deiconify() # Mostrar ya posicionada


def crear_frame_scrollable(parent, bg="#f4f6f9", horizontal=False):
    """
    Crea un contenedor con scroll vertical y, opcionalmente, horizontal.
    Retorna (contenedor, frame_interior).
    """
    contenedor = tk.Frame(parent, bg=bg)
    canvas = tk.Canvas(contenedor, bg=bg, highlightthickness=0, bd=0)
    barra_y = ttk.Scrollbar(contenedor, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=barra_y.set)

    barra_x = None
    if horizontal:
        barra_x = ttk.Scrollbar(contenedor, orient="horizontal", command=canvas.xview)
        canvas.configure(xscrollcommand=barra_x.set)
        barra_x.pack(side="bottom", fill="x")

    barra_y.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    interior = tk.Frame(canvas, bg=bg)
    window_id = canvas.create_window((0, 0), window=interior, anchor="nw")

    def _actualizar_scrollregion(_event=None):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _ajustar_ancho(event):
        if not horizontal:
            canvas.itemconfigure(window_id, width=event.width)

    def _mousewheel(event):
        if not canvas.winfo_exists():
            return
        if horizontal and getattr(event, "state", 0) & 0x0001:
            canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
        else:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _bind_scroll(_event=None):
        canvas.bind_all("<MouseWheel>", _mousewheel)

    def _unbind_scroll(_event=None):
        canvas.unbind_all("<MouseWheel>")

    interior.bind("<Configure>", _actualizar_scrollregion)
    canvas.bind("<Configure>", _ajustar_ancho)
    canvas.bind("<Enter>", _bind_scroll)
    canvas.bind("<Leave>", _unbind_scroll)

    contenedor.canvas = canvas
    contenedor.interior = interior
    contenedor.barra_y = barra_y
    contenedor.barra_x = barra_x
    return contenedor, interior


class AutoScrollbar(ttk.Scrollbar):
    """Una barra de desplazamiento que se oculta automáticamente si no es necesaria."""
    def set(self, lo, hi):
        if float(lo) <= 0.0 and float(hi) >= 1.0:
            self.pack_forget()
        else:
            self.pack(side="right", fill="y")
        super().set(lo, hi)


def preparar_modal_scrollable(ventana, bg="#ffffff", centrar_vertical=False):
    """
    Toma una ventana Toplevel (o Tk) existente y le inyecta un canvas y
    un frame interior desplazable (scrollable).
    Retorna el frame_interior al cual se deben empaquetar los widgets de la ventana.
    
    Esta función abstrae el canvas y la AutoScrollbar para que cualquier modal
    sea auto-desplazable si la pantalla es más pequeña que el contenido.

    Con centrar_vertical=True el contenido queda centrado en alto cuando
    la ventana es más alta que él (en vez de quedar pegado arriba).
    """
    contenedor = tk.Frame(ventana, bg=bg)
    contenedor.pack(fill="both", expand=True)

    canvas = tk.Canvas(contenedor, bg=bg, highlightthickness=0, bd=0)
    # Se crea el AutoScrollbar asociado al canvas
    scrollbar = AutoScrollbar(contenedor, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)

    # El canvas se empaqueta a la izquierda, expandiéndose a todo el espacio disponible
    canvas.pack(side="left", fill="both", expand=True)

    interior = tk.Frame(canvas, bg=bg)
    window_id = canvas.create_window((0, 0), window=interior, anchor="nw")

    def _actualizar_scrollregion(_event=None):
        # Actualiza el scrollregion para abarcar el tamaño del frame interior
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _ajustar_ancho(event):
        # Ajusta el ancho del frame interior al ancho del canvas
        canvas.itemconfigure(window_id, width=event.width)
        if centrar_vertical:
            alto = max(event.height, contenido.winfo_reqheight())
            canvas.itemconfigure(window_id, height=alto)

    def _mousewheel(event):
        if not canvas.winfo_exists():
            return
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _bind_scroll(_event=None):
        canvas.bind_all("<MouseWheel>", _mousewheel)

    def _unbind_scroll(_event=None):
        canvas.unbind_all("<MouseWheel>")

    interior.bind("<Configure>", _actualizar_scrollregion)
    canvas.bind("<Configure>", _ajustar_ancho)
    canvas.bind("<Enter>", _bind_scroll)
    canvas.bind("<Leave>", _unbind_scroll)

    if centrar_vertical:
        contenido = tk.Frame(interior, bg=bg)
        contenido.pack(expand=True, fill="x")
        return contenido
    return interior


def cargar_logo_recortado(ruta, max_ancho, max_alto=None):
    """
    Abre el logo, recorta el margen transparente que pueda traer el PNG
    y lo escala para que quepa en max_ancho x max_alto, así queda
    centrado según el dibujo real y no según el lienzo.
    Retorna un PIL.Image listo para ImageTk.PhotoImage.
    """
    from PIL import Image

    img = Image.open(ruta).convert("RGBA")
    caja = img.getchannel("A").point(lambda v: 255 if v > 10 else 0).getbbox()
    if caja:
        img = img.crop(caja)

    ratio = max_ancho / img.width
    if max_alto:
        ratio = min(ratio, max_alto / img.height)
    nuevo = (max(1, int(img.width * ratio)), max(1, int(img.height * ratio)))
    return img.resize(nuevo, Image.Resampling.LANCZOS)

