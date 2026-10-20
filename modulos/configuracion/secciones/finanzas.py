import tkinter as tk
from tkinter import ttk, messagebox
from ...configuracion.utils import get_configs, set_config
from config import COLOR_BLANCO
from ui_scale import escalar, escalar_fuente
from database.negocio import (
    MODO_PRODUCTOS,
    MODO_SERVICIOS,
    obtener_modo_negocio,
    contar_items_a_convertir,
    establecer_modo_negocio,
)

OPCION_PRODUCTOS = "Productos (almacén, minimarket, tienda)"
OPCION_SERVICIOS = "Servicios (peluquería, taller, consultora)"


class FinanzasSeccion:
    def __init__(self, parent, ui):
        self.parent = parent
        self.ui = ui
        claves = ["iva_porcentaje", "iva_incluido", "redondeo_automatico", "moneda", "regimen_tributario"]
        self.config = get_configs(claves)
        self.construir_ui()

    def construir_ui(self):
        form_frame = self.ui.render_tarjeta(self.parent, "🧾 Configuración de Finanzas e Impuestos")
        form_frame.columnconfigure(1, weight=1)

        # ---------- Tipo de negocio ----------
        lbl_neg = tk.Label(form_frame, text="Tipo de Negocio", font=("Segoe UI", escalar_fuente(11), "bold"), bg=COLOR_BLANCO, fg="#475569")
        lbl_neg.grid(row=0, column=0, columnspan=2, sticky="w", pady=(escalar(5), escalar(10)))

        tk.Label(form_frame, text="El negocio vende:", bg=COLOR_BLANCO).grid(row=1, column=0, sticky="w", padx=escalar(10), pady=escalar(5))
        self.cmb_tipo_negocio = ttk.Combobox(
            form_frame, values=[OPCION_PRODUCTOS, OPCION_SERVICIOS], state="readonly", width=34
        )
        self.cmb_tipo_negocio.grid(row=1, column=1, sticky="w", padx=escalar(10), pady=escalar(5))
        self._modo_inicial = obtener_modo_negocio()
        self.cmb_tipo_negocio.set(
            OPCION_SERVICIOS if self._modo_inicial == MODO_SERVICIOS else OPCION_PRODUCTOS
        )

        tk.Label(
            form_frame,
            text="Un negocio de servicios no maneja stock ni inventario.",
            bg=COLOR_BLANCO, fg="#64748b", font=("Segoe UI", escalar_fuente(8), "italic")
        ).grid(row=2, column=0, columnspan=2, sticky="w", padx=escalar(10), pady=(0, escalar(5)))

        ttk.Separator(form_frame, orient="horizontal").grid(row=3, column=0, columnspan=2, sticky="ew", pady=escalar(15))

        lbl_loc = tk.Label(form_frame, text="Localización y Moneda", font=("Segoe UI", escalar_fuente(11), "bold"), bg=COLOR_BLANCO, fg="#475569")
        lbl_loc.grid(row=4, column=0, columnspan=2, sticky="w", pady=(escalar(5), escalar(10)))

        tk.Label(form_frame, text="Moneda:", bg=COLOR_BLANCO).grid(row=5, column=0, sticky="w", padx=escalar(10), pady=escalar(5))
        # El sistema muestra "$" en todas partes y trabaja con montos
        # enteros (sin decimales), así que la moneda es fija.
        tk.Label(form_frame, text="$ (montos sin decimales)", bg=COLOR_BLANCO,
                 font=("Segoe UI", escalar_fuente(10), "bold")).grid(row=5, column=1, sticky="w", padx=escalar(10), pady=escalar(5))

        tk.Label(form_frame, text="Régimen Tributario:", bg=COLOR_BLANCO).grid(row=6, column=0, sticky="w", padx=escalar(10), pady=escalar(5))
        f_regimen = tk.Frame(form_frame, bg=COLOR_BLANCO)
        f_regimen.grid(row=6, column=1, sticky="w", padx=escalar(10), pady=escalar(5))
        self.cmb_regimen = ttk.Combobox(f_regimen, values=["Pro Pyme (Art 14 D)", "Renta Presunta", "General (Semi Integrado)"], state="readonly", width=30)
        self.cmb_regimen.pack(anchor="w")
        self.cmb_regimen.set(self.config.get("regimen_tributario") or "Pro Pyme (Art 14 D)")
        # El régimen afecta el impuesto a la renta (lo ve el contador), no el IVA
        tk.Label(f_regimen, text="Solo informativo: no cambia precios, IVA ni totales.",
                 bg=COLOR_BLANCO, fg="#64748b", font=("Segoe UI", escalar_fuente(8), "italic")
                 ).pack(anchor="w")

        ttk.Separator(form_frame, orient="horizontal").grid(row=7, column=0, columnspan=2, sticky="ew", pady=escalar(15))
        lbl_base = tk.Label(form_frame, text="Reglas Base de Precios", font=("Segoe UI", escalar_fuente(11), "bold"), bg=COLOR_BLANCO, fg="#475569")
        lbl_base.grid(row=8, column=0, columnspan=2, sticky="w", pady=(escalar(5), escalar(10)))

        tk.Label(form_frame, text="IVA (%) — 0 si no cobras IVA:", bg=COLOR_BLANCO).grid(row=9, column=0, sticky="w", padx=escalar(10), pady=escalar(5))
        self.ent_iva = ttk.Entry(form_frame, width=15)
        self.ent_iva.grid(row=9, column=1, sticky="w", padx=escalar(10), pady=escalar(5))
        self.ent_iva.insert(0, self.config["iva_porcentaje"] or "19.00")

        # Coincidir con el backend (obtener_config_finanzas): "" cuenta como False
        self.var_iva_incluido = tk.BooleanVar(value=self.config["iva_incluido"] in ("1", "True", "true"))
        self.var_redondeo = tk.BooleanVar(value=self.config["redondeo_automatico"] in ("1", "True", "true"))

        # Checkboxes que faltaban: las variables existían y se guardaban,
        # pero no había ningún widget para cambiarlas desde la UI.
        tk.Checkbutton(
            form_frame, text="Los precios de mis productos ya incluyen IVA (lo normal en Chile)",
            variable=self.var_iva_incluido, bg=COLOR_BLANCO, anchor="w",
            font=("Segoe UI", escalar_fuente(10)), command=self._actualizar_ejemplo,
        ).grid(row=10, column=0, columnspan=2, sticky="w", padx=escalar(10), pady=(escalar(10), escalar(2)))

        tk.Checkbutton(
            form_frame, text="Redondear a $10 los pagos en efectivo (Chile)",
            variable=self.var_redondeo, bg=COLOR_BLANCO, anchor="w",
            font=("Segoe UI", escalar_fuente(10)), command=self._actualizar_ejemplo,
        ).grid(row=11, column=0, columnspan=2, sticky="w", padx=escalar(10), pady=escalar(2))

        # Ejemplo en vivo: deja claro qué va a pasar en el POS antes de guardar
        self.lbl_ejemplo = tk.Label(
            form_frame, text="", bg="#f1f5f9", fg="#334155", justify="left", anchor="w",
            font=("Segoe UI", escalar_fuente(9)), padx=escalar(10), pady=escalar(8)
        )
        self.lbl_ejemplo.grid(row=12, column=0, columnspan=2, sticky="ew", padx=escalar(10), pady=(escalar(10), 0))
        self.ent_iva.bind("<KeyRelease>", lambda e: self._actualizar_ejemplo(), add="+")
        self._actualizar_ejemplo()

        tk.Button(
            form_frame, text="💾 Guardar Cambios", bg="#10b981", fg="white", cursor="hand2", 
            relief="flat", font=("Segoe UI", escalar_fuente(10), "bold"), padx=escalar(15), command=self.guardar
        ).grid(row=13, column=0, columnspan=2, pady=escalar(20))

    def _actualizar_ejemplo(self):
        """Muestra cómo queda un producto de $1.235 con la configuración actual."""
        from database.finanzas_utils import calcular_totales_venta

        def pesos(x):
            return "$" + f"{round(x):,}".replace(",", ".")

        try:
            pct = float(self.ent_iva.get().strip().replace(",", ".") or 0)
            if not 0 <= pct <= 100:
                raise ValueError
        except ValueError:
            self.lbl_ejemplo.config(text="Escribe un IVA entre 0 y 100.")
            return

        config = {"iva_porcentaje": pct, "iva_incluido": self.var_iva_incluido.get(),
                  "redondeo_automatico": self.var_redondeo.get()}
        efectivo = calcular_totales_venta(1235, config, "efectivo")
        tarjeta = calcular_totales_venta(1235, config, "tarjeta")

        if pct == 0:
            linea = "Sin IVA: se cobra el precio tal cual."
        elif self.var_iva_incluido.get():
            linea = (f"El precio ya trae el IVA: se cobra {pesos(tarjeta['total'])} "
                     f"(neto {pesos(tarjeta['neto'])} + IVA {pesos(tarjeta['impuesto'])}).")
        else:
            linea = (f"El IVA se suma al precio: se cobra {pesos(tarjeta['total'])} "
                     f"(neto {pesos(tarjeta['neto'])} + IVA {pesos(tarjeta['impuesto'])}).")
        texto = f"Ejemplo, producto de $1.235:  {linea}"
        if efectivo["total"] != tarjeta["total"]:
            texto += (f"\nEn efectivo se redondea a {pesos(efectivo['total'])}; "
                      f"con tarjeta se cobra el monto exacto.")
        self.lbl_ejemplo.config(text=texto)

    def _confirmar_cambio_de_modo(self, modo_actual, destino, detalle, cantidad):
        """Doble confirmación: cambiar de modo convierte ítems y no tiene
        vuelta atrás automática, así que no puede bastar un clic."""
        if not messagebox.askyesno(
            "Cambiar tipo de negocio",
            f"Vas a cambiar el negocio de {modo_actual} a {destino}.\n\n"
            f"{detalle}\n\n"
            "Las ventas ya registradas no se modifican.\n\n"
            "¿Confirmas el cambio?",
            default="no", icon="warning", parent=self.parent
        ):
            return False
        if cantidad == 0:
            return True

        from tkinter import simpledialog
        palabra = destino.upper()
        escrito = simpledialog.askstring(
            "Confirmar cambio",
            f"Para confirmar, escribe {palabra}:",
            parent=self.parent,
        )
        if (escrito or "").strip().upper() != palabra:
            messagebox.showinfo("Cambio cancelado",
                                "No se cambió el tipo de negocio.", parent=self.parent)
            return False
        return True

    def guardar(self):
        # Aceptar coma decimal (formato chileno: "19,5")
        iva_val = self.ent_iva.get().strip().replace(",", ".")
        try:
            iva_float = float(iva_val)
            if iva_float < 0 or iva_float > 100:
                raise ValueError("IVA debe estar entre 0 y 100")
        except ValueError:
            messagebox.showerror("Error de Validación", "El porcentaje de IVA debe ser un número decimal válido entre 0 y 100.", parent=self.parent)
            return

        # ---------- Tipo de negocio (puede convertir ítems) ----------
        mensaje_conversion = ""
        modo_elegido = MODO_SERVICIOS if self.cmb_tipo_negocio.get() == OPCION_SERVICIOS else MODO_PRODUCTOS
        modo_actual = obtener_modo_negocio()

        if modo_elegido != modo_actual:
            cantidad = contar_items_a_convertir(modo_elegido)
            destino = "servicios" if modo_elegido == MODO_SERVICIOS else "productos"

            detalle = f"Se van a convertir {cantidad} ítem(s) a {destino}."
            if cantidad == 0:
                detalle = "No hay ítems que convertir."
            if modo_elegido == MODO_SERVICIOS and cantidad > 0:
                detalle += ("\n\nOJO: al pasar a servicios el stock de esos ítems queda en 0 "
                            "y no se puede recuperar automáticamente.")
            if modo_elegido == MODO_PRODUCTOS and cantidad > 0:
                detalle += ("\n\nOJO: los servicios pasan a ser productos con stock 0. "
                            "No vas a poder venderlos hasta cargarles stock en Productos.")

            if not self._confirmar_cambio_de_modo(modo_actual, destino, detalle, cantidad):
                # Se arrepintió: dejar el combo como estaba y seguir guardando el resto
                self.cmb_tipo_negocio.set(
                    OPCION_SERVICIOS if modo_actual == MODO_SERVICIOS else OPCION_PRODUCTOS
                )
            else:
                convertidos = establecer_modo_negocio(modo_elegido, convertir=True)
                self._modo_inicial = modo_elegido
                mensaje_conversion = (
                    f"\n\nTipo de negocio: {destino} ({convertidos} ítem(s) convertidos)."
                    "\nVuelve al menú principal para ver los cambios en pantalla."
                )

        set_config("iva_porcentaje", iva_val)
        set_config("iva_incluido", "1" if self.var_iva_incluido.get() else "0")
        set_config("redondeo_automatico", "1" if self.var_redondeo.get() else "0")
        set_config("moneda", "$")
        set_config("regimen_tributario", self.cmb_regimen.get())
        
        messagebox.showinfo(
            "Configuración Guardada",
            "Los parámetros financieros se han actualizado correctamente." + mensaje_conversion,
            parent=self.parent
        )
