import tkinter as tk
from tkinter import ttk, messagebox

from database import (
    abrir_caja,
    obtener_caja_abierta,
    obtener_resumen_caja,
    cerrar_caja,
    registrar_movimiento_caja,
)

from modulos.utils_globales import limpiar_formato_numerico, formatear_con_miles
from modulos.seguridad.sesion import Sesion
from ui_scale import escalar, escalar_fuente
from . import caja_ui
from vim_logger import get_logger


class ModuloCaja:
    def __init__(self, root, frame_contenido, volver_menu):
        self.root = root
        self.frame_contenido = frame_contenido
        self.volver_menu = volver_menu

        self.caja_actual = None
        self.tree_movimientos = None

        self.main_frame = None
        self.header_frame = None
        self.content_frame = None

        self.entry_monto_inicial = None

        self.lbl_estado_valor = None
        self.lbl_usuario_valor = None
        self.lbl_fecha_apertura_valor = None
        self.lbl_monto_inicial_valor = None
        self.lbl_ventas_efectivo_valor = None
        self.lbl_ventas_tarjeta_valor = None
        self.lbl_ventas_transferencia_valor = None
        self.lbl_ingresos_valor = None
        self.lbl_egresos_valor = None
        self.lbl_efectivo_esperado_valor = None

        self.btn_abrir_caja = None
        self.btn_ingreso = None
        self.btn_egreso = None
        self.btn_cerrar_caja = None

        caja_ui.construir_ui(self)
        self.cargar_estado_inicial()

    def cargar_estado_inicial(self):
        caja = obtener_caja_abierta()
        if caja:
            self.caja_actual = caja
            self.refrescar_desde_db()
        else:
            self.mostrar_caja_cerrada()

    def formatear_moneda(self, valor):
        try:
            return f"$ {float(valor):,.0f}".replace(",", ".")
        except Exception:
            return "$ 0"

    def mostrar_caja_cerrada(self):
        self.caja_actual = None

        if self.lbl_estado_valor:
            self.lbl_estado_valor.config(text="Cerrada", fg="#d9534f")
        if self.lbl_usuario_valor:
            self.lbl_usuario_valor.config(text="-")
        if self.lbl_fecha_apertura_valor:
            self.lbl_fecha_apertura_valor.config(text="-")
        if self.lbl_monto_inicial_valor:
            self.lbl_monto_inicial_valor.config(text="$ 0")
        if self.lbl_ventas_efectivo_valor:
            self.lbl_ventas_efectivo_valor.config(text="$ 0")
        if self.lbl_ventas_tarjeta_valor:
            self.lbl_ventas_tarjeta_valor.config(text="$ 0")
        if self.lbl_ventas_transferencia_valor:
            self.lbl_ventas_transferencia_valor.config(text="$ 0")
        if self.lbl_ingresos_valor:
            self.lbl_ingresos_valor.config(text="$ 0")
        if self.lbl_egresos_valor:
            self.lbl_egresos_valor.config(text="$ 0")
        if self.lbl_efectivo_esperado_valor:
            self.lbl_efectivo_esperado_valor.config(text="$ 0")

        if self.tree_movimientos:
            self.tree_movimientos.delete(*self.tree_movimientos.get_children())
            self.tree_movimientos.insert("", "end", values=("", "Sin movimientos registrados", "", "", ""), tags=("par",))

        if self.entry_monto_inicial:
            self.entry_monto_inicial.config(state="normal")
            self.entry_monto_inicial.delete(0, "end")
            self.entry_monto_inicial.insert(0, "0")

        if self.btn_abrir_caja:
            self.btn_abrir_caja.config(state="normal")
        if self.btn_ingreso:
            self.btn_ingreso.config(state="disabled")
        if self.btn_egreso:
            self.btn_egreso.config(state="disabled")
        if self.btn_cerrar_caja:
            self.btn_cerrar_caja.config(state="disabled")

    def refrescar_desde_db(self):
        if not self.caja_actual:
            self.mostrar_caja_cerrada()
            return

        resumen = obtener_resumen_caja(self.caja_actual["id"])
        if not resumen:
            self.mostrar_caja_cerrada()
            return

        caja = resumen["caja"]

        self.lbl_estado_valor.config(text="Abierta", fg="#28a745")
        self.lbl_usuario_valor.config(text=str(caja.get("usuario_nombre") or caja.get("usuario_id") or "Sistema"))
        # Formato corto y legible: la fecha cruda de la DB (2026-07-21 15:38:22)
        # es demasiado larga para el chip y se veía recortada.
        fecha_ap = caja.get("fecha_apertura") or "-"
        try:
            from datetime import datetime as _dt
            fecha_ap = _dt.strptime(fecha_ap, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
        except Exception:
            # SILENCIO DELIBERADO: si la fecha viene con otro formato se
            # muestra cruda, que es legible igual. No amerita registro.
            pass
        self.lbl_fecha_apertura_valor.config(text=fecha_ap)
        self.lbl_monto_inicial_valor.config(text=self.formatear_moneda(caja.get("monto_inicial")))
        self.lbl_ventas_efectivo_valor.config(text=self.formatear_moneda(resumen["ventas_efectivo"]))
        self.lbl_ventas_tarjeta_valor.config(text=self.formatear_moneda(resumen["ventas_tarjeta"]))
        self.lbl_ventas_transferencia_valor.config(text=self.formatear_moneda(resumen["ventas_transferencia"]))
        self.lbl_ingresos_valor.config(text=self.formatear_moneda(resumen["ingresos"]))
        self.lbl_egresos_valor.config(text=self.formatear_moneda(resumen["egresos"]))
        self.lbl_efectivo_esperado_valor.config(text=self.formatear_moneda(resumen["efectivo_esperado"]))

        if self.tree_movimientos:
            self.tree_movimientos.delete(*self.tree_movimientos.get_children())
            movimientos = resumen["movimientos"]

            if not movimientos:
                self.tree_movimientos.insert("", "end", values=("", "Sin movimientos registrados", "", "", ""), tags=("par",))
            else:
                # Diccionario para hacer entendible el tipo de movimiento
                traduccion_tipo = {
                    "ingreso": "Ingreso Manual",
                    "egreso": "Egreso Manual",
                    "venta_efectivo": "Venta Efectivo",
                    "venta_tarjeta": "Venta Tarjeta",
                    "venta_transferencia": "Venta Transferencia"
                }

                for i, mov in enumerate(movimientos):
                    tipo_raw = mov.get("tipo", "").lower()
                    
                    # Tipo entendible para humanos
                    tipo_legible = traduccion_tipo.get(tipo_raw, tipo_raw.replace("_", " ").title())
                    
                    # Categoría o referencia extra
                    categoria = mov.get("categoria") or mov.get("referencia_tabla", "Caja")
                    categoria = str(categoria).replace("_", " ").title()
                    
                    # Fecha simplificada (Ejemplo: 12/04 18:30)
                    fecha_raw = str(mov.get("fecha", ""))
                    if fecha_raw and len(fecha_raw) >= 16:
                        try:
                            fecha_raw = fecha_raw.replace("T", " ")
                            partes = fecha_raw.split(" ")
                            yyyy, mm, dd = partes[0].split("-")
                            hhmm = partes[1][:5]
                            hora_legible = f"{dd}/{mm} {hhmm}"
                        except Exception:
                            hora_legible = fecha_raw[:16]
                    else:
                        hora_legible = "—"
                    
                    monto_str = self.formatear_moneda(mov.get("monto", 0))
                    if tipo_raw == "egreso":
                        monto_str = f"- {monto_str}"

                    desc = mov.get("descripcion", "Sin descripción")
                    if not desc.strip():
                        desc = "Sin descripción"

                    tag_color = "impar" if i % 2 != 0 else "par"

                    self.tree_movimientos.insert(
                        "",
                        "end",
                        values=(
                            hora_legible,
                            tipo_legible,
                            categoria,
                            monto_str,
                            desc,
                        ),
                        tags=(tag_color,)
                    )

        if self.entry_monto_inicial:
            self.entry_monto_inicial.config(state="disabled")

        self.btn_abrir_caja.config(state="disabled")
        self.btn_ingreso.config(state="normal")
        self.btn_egreso.config(state="normal")
        self.btn_cerrar_caja.config(state="normal")

    def abrir_caja_real(self, event=None):
        monto = self.entry_monto_inicial.get().strip() if self.entry_monto_inicial else "0"
        monto = limpiar_formato_numerico(monto).replace(",", ".")

        try:
            monto_valor = float(monto or 0)
        except ValueError:
            messagebox.showerror("Error", "El monto inicial no es válido.")
            return

        try:
            self.caja_actual = abrir_caja(monto_valor, usuario_id=Sesion.get_usuario_id())
            messagebox.showinfo("Caja", "Caja abierta correctamente.")
            self.refrescar_desde_db()
        except Exception as e:
            get_logger("caja").exception("Falló una operación de caja")
            messagebox.showerror("Error", str(e))

    def registrar_ingreso(self):
        self._mostrar_dialogo_movimiento("Ingreso", "ingreso")

    def registrar_egreso(self):
        self._mostrar_dialogo_movimiento("Egreso", "egreso")

    def _mostrar_dialogo_movimiento(self, titulo, tipo):
        if not self.caja_actual:
            messagebox.showwarning("Error", "No hay caja abierta.")
            return

        CATEGORIAS_INGRESO = [
            "Ingreso de Efectivo",
            "Depósito Bancario",
            "Ajuste a Favor",
            "Reembolso",
            "Otro Ingreso",
        ]
        CATEGORIAS_EGRESO = [
            "Gasto Operativo",
            "Pago a Proveedor",
            "Servicios Básicos",
            "Retiro de Efectivo",
            "Ajuste en Contra",
            "Otro Egreso",
        ]
        categorias = CATEGORIAS_INGRESO if tipo == "ingreso" else CATEGORIAS_EGRESO

        dialogo = tk.Toplevel(self.root)
        dialogo.title(f"Registrar {titulo}")
        dialogo.config(bg="#ffffff")
        dialogo.transient(self.root)
        dialogo.grab_set()

        from modulos.utils_globales import centrar_ventana_mejorado, preparar_modal_scrollable
        centrar_ventana_mejorado(dialogo, escalar(350), escalar(340), relativo_a=self.root)
        dialogo.minsize(escalar(300), escalar(280))

        body = preparar_modal_scrollable(dialogo, bg="#ffffff")

        tk.Label(body, text="Monto:", font=("Segoe UI", escalar_fuente(10), "bold"), bg="#ffffff").pack(pady=(15, 5))
        entry_monto = tk.Entry(body, font=("Segoe UI", escalar_fuente(12)), justify="center", bd=1, relief="solid")
        entry_monto.pack(pady=5, padx=30, fill="x", ipady=4)
        entry_monto.bind("<KeyRelease>", formatear_con_miles, add="+")

        tk.Label(body, text="Categoría:", font=("Segoe UI", escalar_fuente(10), "bold"), bg="#ffffff").pack(pady=(10, 5))
        combo_categoria = ttk.Combobox(body, values=categorias, state="readonly",
                                        font=("Segoe UI", escalar_fuente(11)), justify="center")
        combo_categoria.set(categorias[0])
        combo_categoria.pack(pady=5, padx=30, fill="x", ipady=2)

        tk.Label(body, text="Descripción:", font=("Segoe UI", escalar_fuente(10), "bold"), bg="#ffffff").pack(pady=(10, 5))
        entry_desc = tk.Entry(body, font=("Segoe UI", escalar_fuente(11)), bd=1, relief="solid")
        entry_desc.pack(pady=5, padx=30, fill="x", ipady=4)

        def confirmar(event=None):
            monto_str = entry_monto.get().strip()
            monto_str = limpiar_formato_numerico(monto_str).replace(",", ".")
            desc = entry_desc.get().strip()
            cat = combo_categoria.get().strip()

            if not monto_str:
                messagebox.showerror("Error", "Debe ingresar un monto.", parent=dialogo)
                return

            try:
                monto = float(monto_str)
                if monto <= 0:
                    messagebox.showerror("Error", "El monto debe ser mayor a 0.", parent=dialogo)
                    return
            except ValueError:
                messagebox.showerror("Error", "Monto inválido.", parent=dialogo)
                return

            try:
                registrar_movimiento_caja(
                    caja_id=self.caja_actual["id"],
                    tipo=tipo,
                    monto=monto,
                    descripcion=desc,
                    usuario_id=Sesion.get_usuario_id(),
                    categoria=cat,
                )
                messagebox.showinfo("Éxito", f"{titulo} registrado correctamente.", parent=dialogo)
                dialogo.destroy()
                self.refrescar_desde_db()
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=dialogo)

        entry_monto.bind("<Return>", confirmar)
        entry_desc.bind("<Return>", confirmar)
        entry_monto.focus()

        btn_confirmar = tk.Button(
            body, text="Confirmar", bg="#4a4a4a", fg="white", font=("Segoe UI", escalar_fuente(10), "bold"),
            command=confirmar, relief="flat", bd=0, activebackground="#333333", activeforeground="white"
        )
        btn_confirmar.pack(pady=(15, 10), padx=30, fill="x", ipady=4)

    def cerrar_caja_real(self):
        if not self.caja_actual:
            messagebox.showwarning("Caja", "No hay caja abierta.")
            return

        try:
            resumen = obtener_resumen_caja(self.caja_actual["id"])
            if not resumen:
                messagebox.showerror("Error", "No se pudo obtener el resumen de la caja.")
                return

            dialogo = tk.Toplevel(self.root)
            dialogo.title("Cierre de Caja")
            dialogo.config(bg="#f8fafc")
            dialogo.transient(self.root)
            dialogo.grab_set()

            from modulos.utils_globales import centrar_ventana_mejorado, preparar_modal_scrollable
            centrar_ventana_mejorado(dialogo, escalar(380), escalar(450), relativo_a=self.root)
            dialogo.minsize(escalar(340), escalar(380))

            body = preparar_modal_scrollable(dialogo, bg="#f8fafc")

            tk.Label(body, text="Resumen de Operaciones", font=("Segoe UI", escalar_fuente(14), "bold"), bg="#f8fafc", fg="#333").pack(pady=(15, 15))

            frame_detalles = tk.Frame(body, bg="#ffffff", bd=1, relief="solid")
            frame_detalles.pack(fill="x", padx=30, pady=(0, 20))

            fondo_inicial = float(resumen["caja"].get("monto_inicial") or 0)
            ventas_efectivo = resumen["ventas_efectivo"]
            ingresos = resumen["ingresos"]
            egresos = resumen["egresos"]
            esperado = resumen["efectivo_esperado"]

            detalles = [
                ("Fondo Inicial:", fondo_inicial),
                ("Ventas en Efectivo:", ventas_efectivo),
                ("Otros Ingresos:", ingresos),
                ("Egresos:", egresos),
            ]

            for titulo, valor in detalles:
                row = tk.Frame(frame_detalles, bg="#ffffff")
                row.pack(fill="x", padx=15, pady=5)
                tk.Label(row, text=titulo, font=("Segoe UI", escalar_fuente(10)), bg="#ffffff").pack(side="left")
                tk.Label(row, text=self.formatear_moneda(valor), font=("Segoe UI", escalar_fuente(10), "bold"), bg="#ffffff").pack(side="right")

            row_esperado = tk.Frame(frame_detalles, bg="#e2e8f0")
            row_esperado.pack(fill="x", pady=(5, 0))
            tk.Label(row_esperado, text="Efectivo Esperado:", font=("Segoe UI", escalar_fuente(11), "bold"), bg="#e2e8f0").pack(side="left", padx=15, pady=8)
            tk.Label(row_esperado, text=self.formatear_moneda(esperado), font=("Segoe UI", escalar_fuente(12), "bold"), bg="#e2e8f0", fg="#2e9e49").pack(side="right", padx=15, pady=8)

            tk.Label(body, text="Monto Contado Real:", font=("Segoe UI", escalar_fuente(11), "bold"), bg="#f8fafc").pack(pady=(5, 5))
            entry_real = tk.Entry(body, font=("Segoe UI", escalar_fuente(14)), justify="center", bd=1, relief="solid", fg="#d85a52")
            entry_real.pack(pady=5, padx=50, fill="x", ipady=4)
            entry_real.bind("<KeyRelease>", formatear_con_miles, add="+")

            def confirmar_cierre(event=None):
                monto_str = entry_real.get().strip()
                monto_str = limpiar_formato_numerico(monto_str).replace(",", ".")

                if not monto_str:
                    messagebox.showerror("Error", "Debe ingresar el monto contado real.", parent=dialogo)
                    return

                try:
                    monto_real = float(monto_str)
                    if monto_real < 0:
                        messagebox.showerror("Error", "El monto real no puede ser negativo.", parent=dialogo)
                        return
                except ValueError:
                    messagebox.showerror("Error", "Monto inválido.", parent=dialogo)
                    return

                diferencia = monto_real - esperado
                
                if diferencia == 0:
                    mensaje_dif = "¡Cuadró exacto! No hay diferencias."
                elif diferencia > 0:
                    mensaje_dif = f"¡Sobró dinero! Hay una diferencia a favor de {self.formatear_moneda(abs(diferencia))}."
                else:
                    mensaje_dif = f"¡Faltó dinero! Hay un faltante de {self.formatear_moneda(abs(diferencia))}."
                
                confirmacion = messagebox.askyesno(
                    "Confirmar Cierre",
                    f"Efectivo Esperado: {self.formatear_moneda(esperado)}\n"
                    f"Efectivo Contado: {self.formatear_moneda(monto_real)}\n\n"
                    f"Resultado: {mensaje_dif}\n\n"
                    f"¿Está seguro de finalizar y cerrar la caja definitivamente?",
                    parent=dialogo
                )
                
                if not confirmacion:
                    return

                try:
                    cerrar_caja(self.caja_actual["id"], monto_cierre=monto_real, usuario_id=Sesion.get_usuario_id())
                    messagebox.showinfo("Caja", "Caja cerrada correctamente.\nEl sistema requiere abrir una nueva caja para procesar ventas.", parent=dialogo)
                    dialogo.destroy()
                    self.mostrar_caja_cerrada()
                except Exception as e:
                    messagebox.showerror("Error", str(e), parent=dialogo)

            entry_real.bind("<Return>", confirmar_cierre)
            entry_real.focus()

            btn_confirmar = tk.Button(
                body, text="Finalizar Cierre", bg="#d85a52", fg="white", font=("Segoe UI", escalar_fuente(11), "bold"),
                command=confirmar_cierre, relief="flat", bd=0, activebackground="#c9302c", activeforeground="white"
            )
            btn_confirmar.pack(pady=(15, 10), padx=50, fill="x", ipady=4)

        except Exception as e:
            get_logger("caja").exception("Falló una operación de caja")
            messagebox.showerror("Error", str(e))


def abrir_modulo_caja(root, frame_contenido, volver_menu):
    return ModuloCaja(root, frame_contenido, volver_menu)