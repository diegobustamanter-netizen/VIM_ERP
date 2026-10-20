import tkinter as tk
import os
import webbrowser
from PIL import Image, ImageTk

from ui_scale import escalar, escalar_fuente

from config import LOGO_PATH, ASSETS_DIR, COLOR_PRIMARIO, COLOR_BLANCO, COLOR_INFO

# ============================================================
# CONSTANTES "ACERCA DE"
# ============================================================

APP_NOMBRE        = "VIM ERP"
APP_SLOGAN        = "Energía para tu empresa"
APP_VERSION       = "1.0"
APP_TIPO          = "POS Local gratuito"
APP_FECHA         = "22 de julio de 2026"
APP_DESARROLLADOR = "Diego Francisco Bustamante Ríos"

APP_OBJETIVO = (
    "VIM ERP fue desarrollado para entregar una solución moderna, rápida y "
    "accesible para pequeños negocios y emprendedores, permitiendo gestionar "
    "ventas, inventario y operaciones de manera simple y eficiente."
)

APP_LICENCIA = "Licencia gratuita para todo emprendedor."
APP_AVISO    = "Se recomienda realizar respaldos periódicos de la información."

# URLs / Redes  (dejar vacío para llenar en el futuro)
REDES = [
    {"nombre": "Instagram",         "icono": "📸", "url": ""},
    {"nombre": "Facebook",          "icono": "📘", "url": ""},
    {"nombre": "Sitio web oficial", "icono": "🌐", "url": ""},
]

# ── Paleta auxiliar ─────────────────────────────────────────
_BG_IZQ      = "#e8eef6"
_BG_DER      = COLOR_BLANCO
_FG_LABEL    = "#475569"
_FG_VALOR    = "#334155"
_FG_MUTED    = "#94a3b8"
_SEP         = "#e2e8f0"
_BG_LICENCIA = "#f0fdf4"
_FG_LICENCIA = "#166534"
_BD_LICENCIA = "#bbf7d0"
_BG_AVISO    = "#fffbeb"
_FG_AVISO    = "#92400e"
_BD_AVISO    = "#fde68a"


# ============================================================
# UTILIDADES
# ============================================================

def _detectar_logo():
    """Devuelve la ruta al logo si existe, o None."""
    # 1. Ruta explícita de config.py (Assets/logo.png)
    if LOGO_PATH and os.path.isfile(LOGO_PATH):
        return LOGO_PATH
    # 2. Fallback: buscar en ASSETS_DIR
    for nombre in ("logo.png", "icono.png"):
        ruta = os.path.join(ASSETS_DIR, nombre)
        if os.path.isfile(ruta):
            return ruta
    # 3. Cualquier imagen en Assets
    if os.path.isdir(ASSETS_DIR):
        for archivo in os.listdir(ASSETS_DIR):
            if archivo.lower().endswith((".png", ".jpg", ".jpeg")):
                return os.path.join(ASSETS_DIR, archivo)
    return None


# ============================================================
# SECCIÓN ACERCA DE
# ============================================================

class AcercaDeSeccion:
    """Sección 'Acerca de' — diseño 2 columnas, sin scroll, sin redundancia."""

    def __init__(self, parent, ui):
        self.parent = parent
        self.ui = ui
        self._imgs = []          # Referencias para evitar GC de imágenes PIL
        self.construir_ui()

    # ──────────────────────────────────────────────────────────
    # LAYOUT RAÍZ
    # ──────────────────────────────────────────────────────────
    def construir_ui(self):
        root = tk.Frame(self.parent, bg=_BG_DER, bd=1, relief="solid")
        root.pack(fill="both", expand=True)

        # Columna izquierda (fija)
        col_izq = tk.Frame(root, bg=_BG_IZQ, width=escalar(310))
        col_izq.pack(side="left", fill="both")
        col_izq.pack_propagate(False)

        # Divisor vertical
        tk.Frame(root, width=1, bg=_SEP).pack(side="left", fill="y")

        # Columna derecha (expansible)
        col_der = tk.Frame(root, bg=_BG_DER)
        col_der.pack(side="left", fill="both", expand=True)

        self._col_izquierda(col_izq)
        self._col_derecha(col_der)

    # ──────────────────────────────────────────────────────────
    # COLUMNA IZQUIERDA — Logo + Desarrollador (solo visual)
    # ──────────────────────────────────────────────────────────
    def _col_izquierda(self, parent):
        # Spacers para centrar verticalmente
        tk.Frame(parent, bg=_BG_IZQ).pack(fill="both", expand=True)

        centro = tk.Frame(parent, bg=_BG_IZQ)
        centro.pack()

        tk.Frame(parent, bg=_BG_IZQ).pack(fill="both", expand=True)

        # ── Logo ──────────────────────────────────────────────
        logo_path = _detectar_logo()
        if logo_path:
            try:
                img = Image.open(logo_path).convert("RGBA")
                max_w, max_h = 200, 140
                img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self._imgs.append(photo)
                lbl_logo = tk.Label(centro, image=photo, bg=_BG_IZQ)
                lbl_logo.image = photo
                lbl_logo.pack(pady=(0, 20))
            except Exception:
                # Fallback texto si falla la imagen
                tk.Label(
                    centro, text=APP_NOMBRE,
                    font=("Segoe UI", escalar_fuente(20), "bold"), fg=COLOR_PRIMARIO, bg=_BG_IZQ
                ).pack(pady=(0, 20))

        # ── Separador ─────────────────────────────────────────
        tk.Frame(centro, height=1, bg=_SEP, width=escalar(180)).pack()

        # ── Desarrollador ─────────────────────────────────────
        tk.Label(
            centro, text="Desarrollado por",
            font=("Segoe UI", escalar_fuente(8)), fg=_FG_MUTED, bg=_BG_IZQ
        ).pack(pady=(16, 0))
        tk.Label(
            centro, text=APP_DESARROLLADOR,
            font=("Segoe UI", escalar_fuente(10), "bold"), fg=COLOR_PRIMARIO, bg=_BG_IZQ,
            wraplength=escalar(250), justify="center"
        ).pack(pady=(4, 0))

    # ──────────────────────────────────────────────────────────
    # COLUMNA DERECHA — Slogan, versión, objetivo, redes, licencia
    # ──────────────────────────────────────────────────────────
    def _col_derecha(self, parent):
        PX = 30
        PT = 24

        # ── Slogan ────────────────────────────────────────────
        slogan_frame = tk.Frame(parent, bg=_BG_DER)
        slogan_frame.pack(fill="x", padx=PX, pady=(PT, 0))
        tk.Label(
            slogan_frame, text=f'"{APP_SLOGAN}"',
            font=("Segoe UI", escalar_fuente(11), "italic"), fg=_FG_LABEL, bg=_BG_DER
        ).pack(anchor="w")

        self._sep(parent, PX)

        # ── Información de versión ────────────────────────────
        sec_ver = tk.Frame(parent, bg=_BG_DER)
        sec_ver.pack(fill="x", padx=PX)
        tk.Label(
            sec_ver, text="📦  Información de versión",
            font=("Segoe UI", escalar_fuente(13), "bold"), fg=COLOR_PRIMARIO, bg=_BG_DER
        ).pack(anchor="w")
        grid_ver = tk.Frame(sec_ver, bg=_BG_DER)
        grid_ver.pack(anchor="w", pady=(8, 0))
        datos_ver = [
            ("Versión:",              APP_VERSION),
            ("Tipo:",                 APP_TIPO),
            ("Fecha de lanzamiento:", APP_FECHA),
        ]
        for i, (etq, val) in enumerate(datos_ver):
            tk.Label(
                grid_ver, text=etq,
                font=("Segoe UI", escalar_fuente(10), "bold"), fg=_FG_LABEL, bg=_BG_DER
            ).grid(row=i, column=0, sticky="w", padx=(0, 14), pady=3)
            tk.Label(
                grid_ver, text=val,
                font=("Segoe UI", escalar_fuente(10)), fg=_FG_VALOR, bg=_BG_DER
            ).grid(row=i, column=1, sticky="w", pady=3)

        self._sep(parent, PX)

        # ── Objetivo ──────────────────────────────────────────
        sec = tk.Frame(parent, bg=_BG_DER)
        sec.pack(fill="x", padx=PX)
        tk.Label(
            sec, text="🎯  Objetivo del sistema",
            font=("Segoe UI", escalar_fuente(13), "bold"), fg=COLOR_PRIMARIO, bg=_BG_DER
        ).pack(anchor="w")
        tk.Label(
            sec, text=APP_OBJETIVO,
            font=("Segoe UI", escalar_fuente(10)), fg=_FG_VALOR, bg=_BG_DER,
            wraplength=escalar(490), justify="left"
        ).pack(anchor="w", pady=(8, 0))

        self._sep(parent, PX)

        # ── Contacto y Redes ──────────────────────────────────
        sec2 = tk.Frame(parent, bg=_BG_DER)
        sec2.pack(fill="x", padx=PX)
        tk.Label(
            sec2, text="🔗  Contacto y Redes Sociales",
            font=("Segoe UI", escalar_fuente(13), "bold"), fg=COLOR_PRIMARIO, bg=_BG_DER
        ).pack(anchor="w")

        grid = tk.Frame(sec2, bg=_BG_DER)
        grid.pack(anchor="w", pady=(10, 0))
        for i, red in enumerate(REDES):
            tk.Label(
                grid, text=f'{red["icono"]}  {red["nombre"]}:',
                font=("Segoe UI", escalar_fuente(10)), fg=_FG_LABEL, bg=_BG_DER,
                width=22, anchor="w"
            ).grid(row=i, column=0, sticky="w", pady=4)

            if red["url"]:
                lbl = tk.Label(
                    grid, text=red["url"],
                    font=("Segoe UI", escalar_fuente(10), "underline"), fg=COLOR_INFO,
                    bg=_BG_DER, cursor="hand2"
                )
                lbl.grid(row=i, column=1, sticky="w", pady=4)
                lbl.bind("<Button-1>", lambda e, u=red["url"]: webbrowser.open(u))
            else:
                tk.Label(
                    grid, text="Próximamente",
                    font=("Segoe UI", escalar_fuente(10), "italic"), fg=_FG_MUTED, bg=_BG_DER
                ).grid(row=i, column=1, sticky="w", pady=4)

        # ── Licencia + Aviso (pegados al fondo) ───────────────
        bottom = tk.Frame(parent, bg=_BG_DER)
        bottom.pack(fill="x", padx=PX, pady=(0, PT), side="bottom")

        aviso = tk.Frame(
            bottom, bg=_BG_AVISO,
            highlightbackground=_BD_AVISO, highlightthickness=1
        )
        aviso.pack(fill="x", side="bottom", pady=(6, 0))
        tk.Label(
            aviso, text=f"⚠️  {APP_AVISO}",
            font=("Segoe UI", escalar_fuente(9)), fg=_FG_AVISO, bg=_BG_AVISO
        ).pack(padx=14, pady=6)

        lic = tk.Frame(
            bottom, bg=_BG_LICENCIA,
            highlightbackground=_BD_LICENCIA, highlightthickness=1
        )
        lic.pack(fill="x", side="bottom")
        tk.Label(
            lic, text=f"📄  {APP_LICENCIA}",
            font=("Segoe UI", escalar_fuente(10), "bold"), fg=_FG_LICENCIA, bg=_BG_LICENCIA
        ).pack(padx=14, pady=6)

    # ──────────────────────────────────────────────────────────
    # UTILIDADES
    # ──────────────────────────────────────────────────────────
    @staticmethod
    def _sep(parent, padx=20):
        tk.Frame(parent, height=1, bg=_SEP).pack(fill="x", padx=padx, pady=16)
