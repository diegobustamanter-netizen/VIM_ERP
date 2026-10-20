import tkinter as tk
from tkinter import ttk, messagebox
from ...configuracion.utils import get_configs, set_config
from ui_scale import escalar, escalar_fuente

class VentasSeccion:
    def __init__(self, parent, ui):
        self.parent = parent
        self.ui = ui
        claves = ["ticket_tamano", "ticket_desglose_iva", "ticket_mensaje_pie", "ticket_copias"]
        self.config = get_configs(claves)
        self.construir_ui()

    def construir_ui(self):
        frame = self.ui.render_tarjeta(self.parent, "🛒 Configuración de Ventas y Tickets")
        
        tk.Label(frame, text="Tamaño del Papel Térmico:", bg="white").grid(row=0, column=0, sticky="w", pady=escalar(5))
        self.cmb_tamano = ttk.Combobox(frame, values=["58mm", "80mm", "A4"], state="readonly", width=15)
        self.cmb_tamano.grid(row=0, column=1, padx=escalar(10), pady=escalar(5), sticky="w")
        self.cmb_tamano.set(self.config["ticket_tamano"] or "58mm")
        
        self.var_iva = tk.BooleanVar(value=True if self.config["ticket_desglose_iva"] in ("1", "True", "true", "") else False)
        tk.Checkbutton(frame, text="Imprimir resumen de base imponible e IVA", variable=self.var_iva, bg="white").grid(row=1, column=0, columnspan=2, sticky="w", pady=escalar(5))
        
        tk.Label(frame, text="Número de copias por defecto:", bg="white").grid(row=2, column=0, sticky="w", pady=escalar(5))
        self.spin_copias = tk.Spinbox(frame, from_=1, to=5, width=5)
        self.spin_copias.grid(row=2, column=1, padx=escalar(10), pady=escalar(5), sticky="w")
        self.spin_copias.delete(0, tk.END)
        self.spin_copias.insert(0, self.config["ticket_copias"] or "1")
        
        tk.Label(frame, text="Mensaje de pie de ticket:", bg="white").grid(row=3, column=0, sticky="w", pady=(escalar(15), escalar(5)))
        self.ent_pie = tk.Entry(frame, width=50)
        self.ent_pie.grid(row=3, column=1, padx=escalar(10), pady=(escalar(15), escalar(5)), sticky="w")
        self.ent_pie.insert(0, self.config["ticket_mensaje_pie"] or "¡Gracias por su compra!")
        
        tk.Button(
            frame, text="Guardar Preferencias", bg="#28a745", fg="white", cursor="hand2", 
            relief="flat", font=("Segoe UI", escalar_fuente(10), "bold"), command=self.guardar
        ).grid(row=4, column=0, columnspan=2, pady=escalar(20))

    def guardar(self):
        set_config("ticket_tamano", self.cmb_tamano.get())
        set_config("ticket_desglose_iva", "1" if self.var_iva.get() else "0")
        set_config("ticket_copias", self.spin_copias.get())
        set_config("ticket_mensaje_pie", self.ent_pie.get().strip())
        
        messagebox.showinfo("Éxito", "Configuración de tickets guardada.", parent=self.parent)
