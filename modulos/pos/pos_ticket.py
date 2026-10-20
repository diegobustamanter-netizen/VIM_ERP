from tkinter import messagebox, simpledialog
from database.productos import obtener_producto_por_id
from database.ventas import confirmar_venta
from .pos_utils import convertir_float, moneda, numero
from .pos_calculos import estado_del_pago
from ui_scale import escalar_fuente
from vim_logger import get_logger


class POSTicketMixin:
    """Armado del ticket, cobro y cierre de la venta.

    Métodos de ModuloPOS (ver pos_main.py). Antes se asignaban a mano
    a la clase, uno por uno, al final de aquel archivo.
    """

    def focus_campo_venta(self):
        producto = self.obtener_producto_seleccionado()
        if not producto:
            return

        if producto.get("tipo_venta") == "peso":
            self.entry_peso.config(state="normal")
            self.entry_peso.focus_set()
            self.entry_peso.select_range(0, "end")
        else:
            self.entry_cantidad.config(state="normal")
            self.entry_cantidad.focus_set()
            self.entry_cantidad.select_range(0, "end")


    def actualizar_modo_venta(self, producto=None):
        if not producto:
            self.lbl_modo.config(text="Modo: sin producto seleccionado")
            self.entry_cantidad.config(state="normal")
            self.entry_peso.config(state="normal")
            return

        tipo = producto.get("tipo_venta") or "unidad"
        nombre = producto.get("nombre") or ""

        if tipo == "peso":
            self.lbl_modo.config(text=f"Modo: {nombre} se vende por peso")

            self.entry_cantidad.config(state="normal")
            self.entry_cantidad.delete(0, "end")
            self.entry_cantidad.insert(0, "1")
            self.entry_cantidad.config(state="disabled")

            self.entry_peso.config(state="normal")
            if not self.entry_peso.get().strip():
                self.entry_peso.insert(0, "1")
        else:
            self.lbl_modo.config(text=f"Modo: {nombre} se vende por unidad")

            self.entry_peso.config(state="normal")
            self.entry_peso.delete(0, "end")
            self.entry_peso.insert(0, "1")
            self.entry_peso.config(state="disabled")

            self.entry_cantidad.config(state="normal")
            if not self.entry_cantidad.get().strip():
                self.entry_cantidad.insert(0, "1")


    def focus_siguiente_desde_cantidad(self):
        seleccion = self.obtener_producto_seleccionado()
        if not seleccion:
            self.entry_peso.focus_set()
            self.entry_peso.select_range(0, "end")
            return

        if seleccion.get("tipo_venta") == "unidad":
            self.agregar_producto_seleccionado()
        else:
            self.entry_peso.focus_set()
            self.entry_peso.select_range(0, "end")


    def focus_siguiente_desde_peso(self):
        self.agregar_producto_seleccionado()


    def agregar_producto_seleccionado(self):
        producto = self.obtener_producto_seleccionado()
        if not producto:
            messagebox.showwarning("Atención", "Selecciona un producto.")
            return

        tipo_venta = producto.get("tipo_venta") or "unidad"
        nombre = producto.get("nombre") or ""
        stock = convertir_float(producto.get("stock"), 0)
        tipo_item = producto.get("tipo_item") or "producto"

        if tipo_venta == "unidad":
            cantidad = convertir_float(self.entry_cantidad.get(), 1)

            if cantidad <= 0:
                messagebox.showwarning("Atención", "Ingresa una cantidad válida.")
                self.entry_cantidad.focus_set()
                return

            if tipo_item != "servicio" and cantidad > stock:
                messagebox.showwarning(
                    "Stock insuficiente",
                    f"Stock disponible para {nombre}: {numero(stock)}"
                )
                return

            precio_unitario = convertir_float(producto.get("precio_venta"), 0)
            subtotal = cantidad * precio_unitario

            linea_nueva = {
                "producto_id": producto.get("id"),
                "nombre": nombre,
                "tipo_venta": "unidad",
                "tipo_item": tipo_item,
                "cantidad": cantidad,
                "peso": 0,
                "precio_unitario": precio_unitario,
                "precio_por_kilo": 0,
                "subtotal": subtotal,
            }

        else:
            peso = convertir_float(self.entry_peso.get(), 1)

            if peso <= 0:
                messagebox.showwarning("Atención", "Ingresa un peso válido en kilos.")
                self.entry_peso.focus_set()
                return

            if tipo_item != "servicio" and peso > stock:
                messagebox.showwarning(
                    "Stock insuficiente",
                    f"Stock disponible para {nombre}: {numero(stock)} kg"
                )
                return

            precio_kilo = convertir_float(producto.get("precio_por_kilo"), 0)
            subtotal = peso * precio_kilo

            linea_nueva = {
                "producto_id": producto.get("id"),
                "nombre": nombre,
                "tipo_venta": "peso",
                "tipo_item": tipo_item,
                "cantidad": 0,
                "peso": peso,
                "precio_unitario": 0,
                "precio_por_kilo": precio_kilo,
                "subtotal": subtotal,
            }

        for linea in self.ticket:
            mismo_producto = linea["producto_id"] == linea_nueva["producto_id"]
            mismo_tipo = linea["tipo_venta"] == linea_nueva["tipo_venta"]

            if mismo_producto and mismo_tipo:
                if linea["tipo_venta"] == "unidad":
                    nueva_cantidad = convertir_float(linea["cantidad"]) + convertir_float(linea_nueva["cantidad"])

                    if tipo_item != "servicio" and nueva_cantidad > stock:
                        messagebox.showwarning(
                            "Stock insuficiente",
                            f"Stock disponible para {nombre}: {numero(stock)}"
                        )
                        return

                    linea["cantidad"] = nueva_cantidad
                    linea["subtotal"] = nueva_cantidad * convertir_float(linea["precio_unitario"])

                else:
                    nuevo_peso = convertir_float(linea["peso"]) + convertir_float(linea_nueva["peso"])

                    if tipo_item != "servicio" and nuevo_peso > stock:
                        messagebox.showwarning(
                            "Stock insuficiente",
                            f"Stock disponible para {nombre}: {numero(stock)} kg"
                        )
                        return

                    linea["peso"] = nuevo_peso
                    linea["subtotal"] = nuevo_peso * convertir_float(linea["precio_por_kilo"])

                self.refrescar_ticket()
                self.limpiar_campos_entrada_producto()
                return

        self.ticket.append(linea_nueva)
        self.refrescar_ticket()
        self.limpiar_campos_entrada_producto()


    def limpiar_campos_entrada_producto(self):
        self.entry_busqueda.delete(0, "end")

        self.entry_cantidad.config(state="normal")
        self.entry_cantidad.delete(0, "end")
        self.entry_cantidad.insert(0, "1")

        self.entry_peso.config(state="normal")
        self.entry_peso.delete(0, "end")
        self.entry_peso.insert(0, "1")

        self.limpiar_tabla_productos()
        self.actualizar_modo_venta(None)

        # Volver a mostrar el catálogo completo.
        #
        # Se probó no recargarlo, para ahorrar la consulta. Fue un error: al
        # agregar un producto la lista quedaba vacía y parecía que se hubieran
        # borrado todos. El cajero necesita ver el catálogo entre producto y
        # producto, sobre todo si busca a mano en vez de escanear.
        #
        # El ahorro real de rendimiento vino del debounce de la búsqueda
        # (ver pos_ui), no de esto.
        self.mostrar_todos()
        self.entry_busqueda.focus_set()


    def refrescar_ticket(self):
        for item in self.tree_ticket.get_children():
            self.tree_ticket.delete(item)

        total = 0

        for i, linea in enumerate(self.ticket):
            tipo_venta = linea.get("tipo_venta", "unidad")

            if tipo_venta == "unidad":
                cantidad_peso = numero(linea["cantidad"])
                precio = moneda(convertir_float(linea["precio_unitario"]))
            else:
                cantidad_peso = f"{numero(linea['peso'])} kg"
                precio = moneda(convertir_float(linea["precio_por_kilo"]))

            subtotal = convertir_float(linea["subtotal"])
            total += subtotal

            tag = "ultimo" if i == len(self.ticket) - 1 else ""

            self.tree_ticket.insert(
                "",
                "end",
                values=(
                    linea["nombre"],
                    cantidad_peso,
                    precio,
                    moneda(subtotal),
                ),
                tags=(tag,)
            )

        # Ajuste adaptativo de fuente para el TOTAL grande
        if total >= 1000000:
            nueva_fuente = ("Segoe UI", escalar_fuente(22, minimo=16, maximo=24), "bold")
        elif total >= 100000:
            nueva_fuente = ("Segoe UI", escalar_fuente(26, minimo=18, maximo=28), "bold")
        else:
            nueva_fuente = ("Segoe UI", escalar_fuente(32, minimo=22, maximo=34), "bold")
        
        self.lbl_total.config(font=nueva_fuente, text=f"Total: {moneda(total)}")
        self.lbl_items.config(text=f"Líneas: {len(self.ticket)}")
        self.actualizar_vuelto()


    def obtener_indice_linea_seleccionada(self):
        seleccion = self.tree_ticket.selection()
        if not seleccion:
            return None

        item_id = seleccion[0]
        index = self.tree_ticket.index(item_id)

        if index < 0 or index >= len(self.ticket):
            return None

        return index


    def editar_linea_ticket(self):
        index = self.obtener_indice_linea_seleccionada()
        if index is None:
            messagebox.showwarning("Atención", "Selecciona una línea del ticket.")
            return

        linea = self.ticket[index]
        producto = obtener_producto_por_id(linea["producto_id"])

        if not producto:
            messagebox.showerror("Error", "Producto no encontrado.")
            return

        stock = convertir_float(producto.get("stock"), 0)
        tipo_item = producto.get("tipo_item") or "producto"

        if linea["tipo_venta"] == "unidad":
            nueva_cantidad = simpledialog.askfloat(
                "Editar cantidad",
                f"Ingrese nueva cantidad para {linea['nombre']}:",
                initialvalue=convertir_float(linea["cantidad"]),
                minvalue=0.01,
                parent=self.root
            )

            if nueva_cantidad is None:
                return

            if tipo_item != "servicio" and nueva_cantidad > stock:
                messagebox.showwarning("Stock insuficiente", f"Stock disponible: {numero(stock)}")
                return

            linea["cantidad"] = nueva_cantidad
            linea["subtotal"] = nueva_cantidad * convertir_float(linea["precio_unitario"])

            # Opcional: Modificar precio manualmente (Protegido)
            from modulos.seguridad.autorizacion_ui import solicitar_autorizacion_admin
            if messagebox.askyesno("Precio", "¿Desea modificar el PRECIO UNITARIO de este producto?", parent=self.root):
                if solicitar_autorizacion_admin(self.root, f"Modificar precio de {linea['nombre']}"):
                    nuevo_p = simpledialog.askfloat(
                        "Nuevo Precio",
                        f"Precio actual: {linea['precio_unitario']}\nIngrese nuevo precio:",
                        minvalue=0,
                        parent=self.root
                    )
                    if nuevo_p is not None:
                        linea["precio_unitario"] = nuevo_p
                        linea["subtotal"] = nueva_cantidad * nuevo_p
                        # Marca la línea para que confirmar_venta() envíe este precio
                        # a la BD. Sin esta marca, crear_venta() recalcula desde el
                        # precio de catálogo y el cambio autorizado se perdía.
                        linea["precio_modificado"] = True

        else:
            nuevo_peso = simpledialog.askfloat(
                "Editar peso",
                f"Ingrese nuevo peso (kg) para {linea['nombre']}:",
                initialvalue=convertir_float(linea["peso"]),
                minvalue=0.001,
                parent=self.root
            )

            if nuevo_peso is None:
                return

            if tipo_item != "servicio" and nuevo_peso > stock:
                messagebox.showwarning("Stock insuficiente", f"Stock disponible: {numero(stock)} kg")
                return

            linea["peso"] = nuevo_peso
            linea["subtotal"] = nuevo_peso * convertir_float(linea["precio_por_kilo"])

        self.refrescar_ticket()


    def eliminar_linea_ticket(self):
        index = self.obtener_indice_linea_seleccionada()
        if index is None:
            messagebox.showwarning("Atención", "Selecciona una línea del ticket.")
            return

        # Corregir un ticket suele implicar sacar varias líneas seguidas: tras
        # autorizar una vez, no se vuelve a pedir la clave por un minuto.
        from modulos.seguridad.autorizacion_ui import (
            solicitar_autorizacion_admin, VENTANA_GRACIA_SEGUNDOS
        )
        from modulos.seguridad.sesion import Sesion

        AMBITO = "eliminar_linea_ticket"
        venia_autorizado = Sesion.autorizacion_vigente(AMBITO, VENTANA_GRACIA_SEGUNDOS)

        if not solicitar_autorizacion_admin(
            self.root, "Eliminar línea del ticket", ambito=AMBITO
        ):
            return

        nota_gracia = ""
        if venia_autorizado:
            restantes = Sesion.segundos_restantes_autorizacion(AMBITO, VENTANA_GRACIA_SEGUNDOS)
            nota_gracia = (f"\n\n(Autorización vigente por {restantes}s más, "
                           "por eso no se pidió la contraseña.)")

        confirmar = messagebox.askyesno(
            "Confirmar eliminación",
            f"¿Deseas eliminar la línea seleccionada del ticket?{nota_gracia}"
        )
        if not confirmar:
            return

        del self.ticket[index]
        self.refrescar_ticket()

        if self.ticket:
            hijos = self.tree_ticket.get_children()
            if hijos:
                nuevo_index = min(index, len(hijos) - 1)
                self.tree_ticket.selection_set(hijos[nuevo_index])
                self.tree_ticket.focus(hijos[nuevo_index])
        else:
            self.entry_busqueda.focus_set()


    def vaciar_ticket(self):
        if not self.ticket:
            self.entry_busqueda.focus_set()
            return

        from modulos.seguridad.autorizacion_ui import solicitar_autorizacion_admin
        if not solicitar_autorizacion_admin(self.root, "Vaciar el ticket completo"):
            return

        confirmar = messagebox.askyesno("Confirmar", "¿Deseas vaciar el ticket completo?")
        if not confirmar:
            return

        self.ticket.clear()
        self.entry_pago_cliente.delete(0, "end")
        self.limpiar_campos_entrada_producto()
        self.actualizar_vuelto()


    def calcular_total(self):
        return sum(convertir_float(linea["subtotal"]) for linea in self.ticket)


    def actualizar_vuelto(self):
        """Pinta el vuelto, o cuánto falta si el pago no alcanza.

        La decisión vive en pos_calculos.estado_del_pago (sin tkinter, con
        pruebas). Acá solo se actualizan los widgets.
        """
        estado = estado_del_pago(
            self.calcular_total(),
            convertir_float(self.entry_pago_cliente.get(), 0),
        )

        self.lbl_vuelto.config(
            text=moneda(estado["monto"]), fg=estado["color"], bg=estado["fondo"]
        )

        # El título y el marco solo existen si la UI ya los creó
        titulo = getattr(self, "lbl_vuelto_titulo", None)
        if titulo is not None:
            titulo.config(text=estado["titulo"], fg=estado["color"], bg=estado["fondo"])

        marco = getattr(self, "frame_vuelto", None)
        if marco is not None:
            marco.config(bg=estado["fondo"])


    def confirmar_venta_ticket(self, metodo_pago="efectivo"):
        if not self.ticket:
            messagebox.showwarning("Atención", "El ticket está vacío.")
            return

        total = self.calcular_total()
    
        if metodo_pago == "efectivo":
            pago = convertir_float(self.entry_pago_cliente.get(), 0)

            if pago <= 0:
                messagebox.showwarning("Atención", "Ingresa el pago del cliente en efectivo.")
                self.entry_pago_cliente.focus_set()
                return

            if pago < total:
                messagebox.showwarning(
                    "Pago insuficiente",
                    f"El pago del cliente no cubre el total.\n\n"
                    f"Total: {moneda(total)}\n"
                    f"Pago: {moneda(pago)}"
                )
                self.entry_pago_cliente.focus_set()
                self.entry_pago_cliente.select_range(0, "end")
                return
        
            vuelto = pago - total
        else:
            pago = total
            vuelto = 0

        from modulos.seguridad.sesion import Sesion
        ok, mensaje, venta_id = confirmar_venta(
            self.ticket, pago, 
            metodo_pago=metodo_pago, 
            usuario_id=Sesion.get_usuario_id()
        )

        if ok:
            # Snapshot de las líneas ANTES de limpiar el ticket, para la
            # impresión térmica (automática y/o el botón del recibo digital)
            lineas_impresion = _preparar_lineas_impresion(self.ticket)

            # Folio real, consultado una sola vez. Antes el recibo en pantalla
            # inventaba uno a partir del id ("VTA-000123") que no coincidía con
            # el guardado en la base ni con el que imprime la térmica.
            from database.ventas import obtener_folio_venta
            folio = obtener_folio_venta(venta_id) or f"VTA-{venta_id:06d}"

            # Impresión térmica automática (si hay impresora configurada).
            # NUNCA bloquea la venta: cualquier error solo se informa.
            _imprimir_ticket_fisico(venta_id, metodo_pago, total, pago, vuelto,
                                    lineas_impresion, silencioso=False, parent=self.root,
                                    folio=folio)

            # Mostrar recibo digital
            _mostrar_recibo_digital(self, venta_id, metodo_pago, total, pago, vuelto,
                                    lineas_impresion=lineas_impresion, folio=folio)

            self.ticket.clear()
            self.refrescar_ticket()
            self.entry_pago_cliente.delete(0, "end")
            self.actualizar_vuelto()
            self.limpiar_campos_entrada_producto()
        else:
            messagebox.showerror("Error al registrar venta", mensaje)


def _preparar_lineas_impresion(ticket):
    """Convierte las líneas del ticket POS al formato del módulo de impresión."""
    lineas = []
    for linea in ticket:
        if linea.get("tipo_venta") == "unidad":
            cant_txt = f"x{numero(linea['cantidad'])}"
        else:
            cant_txt = f"{numero(linea['peso'])} kg"
        lineas.append({
            "nombre": linea.get("nombre", ""),
            "cantidad_txt": cant_txt,
            "subtotal": convertir_float(linea.get("subtotal")),
        })
    return lineas


def _imprimir_ticket_fisico(venta_id, metodo_pago, total, pago, vuelto,
                            lineas_impresion, silencioso=True, parent=None,
                            forzar=False, folio=None):
    """Imprime el ticket en la impresora térmica configurada.

    - Si no hay impresora configurada, o la impresión automática está
      desactivada (y no es `forzar`), no hace nada.
    - Los errores JAMÁS interrumpen la venta: se registran en el log y,
      si silencioso=False, se muestran una única vez por sesión.
    Retorna True si se imprimió.
    """
    global _error_impresion_mostrado
    try:
        from modulos.impresion import imprimir_ticket_venta, impresora_configurada
        from modulos.configuracion.utils import get_config
        from database.utils import ahora as ahora_util
        from modulos.seguridad.sesion import Sesion
        from database.connection import session_db

        if not impresora_configurada():
            return False
        if not forzar and get_config("impresion_automatica", "1") not in ("1", "True", "true"):
            return False

        # El folio ya viene resuelto por quien llama; solo falta el impuesto.
        folio_final, impuesto = folio or f"VTA-{venta_id:06d}", 0
        try:
            with session_db(dict_rows=True) as conn:
                fila = conn.execute(
                    "SELECT folio, impuesto FROM ventas WHERE id = ?", (venta_id,)
                ).fetchone()
                if fila:
                    folio_final = folio or fila.get("folio") or folio_final
                    impuesto = fila.get("impuesto") or 0
        except Exception as e:
            # Con folio/impuesto por defecto igual se puede imprimir
            from vim_logger import get_logger
            get_logger("pos.impresion").warning(
                f"No se pudo leer folio/impuesto de la venta #{venta_id}: {e}"
            )

        datos = {
            "folio": folio_final,
            "fecha": ahora_util("%d/%m/%Y %H:%M"),
            "cajero": Sesion.get_nombre(),
            "metodo_pago": metodo_pago,
            "lineas": lineas_impresion,
            "impuesto": impuesto,
            "total": total,
            "pago": pago,
            "vuelto": vuelto,
        }
        imprimir_ticket_venta(datos)
        return True
    except Exception as e:
        from vim_logger import get_logger
        get_logger("pos.impresion").error(f"Error imprimiendo ticket venta #{venta_id}: {e}")
        if not silencioso and not _error_impresion_mostrado:
            _error_impresion_mostrado = True
            messagebox.showwarning(
                "Impresora",
                f"La venta se registró correctamente, pero no se pudo imprimir el ticket:\n\n{e}\n\n"
                "Puede reintentar desde el botón 🖨 del recibo. "
                "(Este aviso no volverá a mostrarse en esta sesión.)",
                parent=parent
            )
        return False


_error_impresion_mostrado = False


def _mostrar_recibo_digital(self, venta_id, metodo_pago, total, pago, vuelto,
                            lineas_impresion=None, folio=None):
    """Muestra un recibo digital tipo ticket después de confirmar la venta."""
    import tkinter as tk
    from database.utils import ahora as ahora_util
    from modulos.utils_globales import centrar_ventana_mejorado, crear_frame_scrollable
    from ui_scale import escalar

    top = tk.Toplevel(self.root)
    top.title(f"Recibo - Venta #{venta_id}")
    top.configure(bg="white")
    top.attributes("-topmost", True)
    top.lift()
    top.grab_set()

    try:
        from modulos.utils_globales import aplicar_barra_windows_azul
        aplicar_barra_windows_azul(top)
    except Exception:
        pass

    centrar_ventana_mejorado(top, escalar(400), escalar(560), relativo_a=self.root)
    top.minsize(escalar(320), escalar(400))

    # Nombre del negocio
    try:
        from modulos.configuracion.utils import get_config
        nombre_negocio = get_config("nombre_negocio", "VIM ERP")
        msg_pie = get_config("ticket_mensaje_pie", "¡Gracias por su compra!")
    except Exception:
        get_logger("pos.ticket").exception("No se pudo leer nombre/mensaje del ticket (se usan valores por defecto)")
        nombre_negocio = "VIM ERP"
        msg_pie = "¡Gracias por su compra!"

    # Frame scrollable para tickets largos
    scroll_cont, interior = crear_frame_scrollable(top, bg="white")
    scroll_cont.pack(fill="both", expand=True, padx=20, pady=(15, 5))

    # Encabezado
    tk.Label(interior, text=nombre_negocio, font=("Segoe UI", escalar_fuente(16), "bold"),
             fg="#002b5c", bg="white").pack(pady=(5, 2))
    tk.Label(interior, text="═" * 40, font=("Consolas", escalar_fuente(8)),
             fg="#ccc", bg="white").pack()

    ahora_str = ahora_util("%d/%m/%Y  %H:%M")
    folio_mostrar = folio or f"VTA-{venta_id:06d}"
    tk.Label(interior, text=f"Folio: {folio_mostrar}    {ahora_str}",
             font=("Segoe UI", escalar_fuente(8)), fg="#666", bg="white").pack(pady=(4, 0))
    tk.Label(interior, text=f"Método: {metodo_pago.capitalize()}",
             font=("Segoe UI", escalar_fuente(8)), fg="#666", bg="white").pack()
    tk.Label(interior, text="─" * 48, font=("Consolas", escalar_fuente(8)),
             fg="#ddd", bg="white").pack(pady=(4, 4))

    # Detalle de productos
    for linea in self.ticket:
        nombre_prod = linea["nombre"]
        if len(nombre_prod) > 24:
            nombre_prod = nombre_prod[:22] + ".."

        if linea["tipo_venta"] == "unidad":
            cant_txt = f"x{numero(linea['cantidad'])}"
        else:
            cant_txt = f"{numero(linea['peso'])}kg"

        subtotal = moneda(convertir_float(linea["subtotal"]))

        row = tk.Frame(interior, bg="white")
        row.pack(fill="x", padx=5, pady=1)
        tk.Label(row, text=nombre_prod, font=("Segoe UI", escalar_fuente(9)),
                 fg="#333", bg="white", anchor="w").pack(side="left", fill="x", expand=True)
        tk.Label(row, text=cant_txt, font=("Segoe UI", escalar_fuente(8)),
                 fg="#888", bg="white").pack(side="left", padx=(5, 8))
        tk.Label(row, text=subtotal, font=("Segoe UI", escalar_fuente(9), "bold"),
                 fg="#333", bg="white", anchor="e").pack(side="right")

    tk.Label(interior, text="─" * 48, font=("Consolas", escalar_fuente(8)),
             fg="#ddd", bg="white").pack(pady=(6, 4))

    # Totales
    row_total = tk.Frame(interior, bg="white")
    row_total.pack(fill="x", padx=5, pady=(2, 4))
    tk.Label(row_total, text="TOTAL:", font=("Segoe UI", escalar_fuente(14), "bold"),
             fg="#002b5c", bg="white", anchor="w").pack(side="left")
    tk.Label(row_total, text=moneda(total), font=("Segoe UI", escalar_fuente(14), "bold"),
             fg="#002b5c", bg="white", anchor="e").pack(side="right")

    if metodo_pago == "efectivo":
        row_pago = tk.Frame(interior, bg="white")
        row_pago.pack(fill="x", padx=5)
        tk.Label(row_pago, text="Pago:", font=("Segoe UI", escalar_fuente(10)),
                 fg="#555", bg="white", anchor="w").pack(side="left")
        tk.Label(row_pago, text=moneda(pago), font=("Segoe UI", escalar_fuente(10)),
                 fg="#555", bg="white", anchor="e").pack(side="right")

        row_vuelto = tk.Frame(interior, bg="white")
        row_vuelto.pack(fill="x", padx=5, pady=(2, 0))
        tk.Label(row_vuelto, text="VUELTO:", font=("Segoe UI", escalar_fuente(12), "bold"),
                 fg="#28a745", bg="white", anchor="w").pack(side="left")
        tk.Label(row_vuelto, text=moneda(vuelto), font=("Segoe UI", escalar_fuente(12), "bold"),
                 fg="#28a745", bg="white", anchor="e").pack(side="right")

    tk.Label(interior, text="═" * 40, font=("Consolas", escalar_fuente(8)),
             fg="#ccc", bg="white").pack(pady=(8, 2))
    tk.Label(interior, text=msg_pie, font=("Segoe UI", escalar_fuente(9), "italic"),
             fg="#888", bg="white").pack(pady=(0, 8))

    # Botones — fuera del scroll, siempre visibles
    f_botones = tk.Frame(top, bg="white")
    f_botones.pack(fill="x", padx=20, pady=(5, 15))

    # Botón imprimir/reimprimir (solo si hay impresora configurada)
    try:
        from modulos.impresion import impresora_configurada
        hay_impresora = bool(impresora_configurada())
    except Exception:
        get_logger("pos.ticket").exception("No se pudo comprobar la impresora configurada")
        hay_impresora = False

    if hay_impresora and lineas_impresion:
        def _reimprimir():
            ok_imp = _imprimir_ticket_fisico(
                venta_id, metodo_pago, total, pago, vuelto,
                lineas_impresion, silencioso=True, parent=top, forzar=True,
                folio=folio
            )
            if ok_imp:
                messagebox.showinfo("Impresora", "Ticket enviado a la impresora.", parent=top)
            else:
                messagebox.showwarning(
                    "Impresora",
                    "No se pudo imprimir el ticket. Revise que la impresora esté "
                    "encendida y con papel (detalle en el log del sistema).",
                    parent=top
                )

        tk.Button(
            f_botones, text="🖨 Imprimir", bg="#0ea5e9", fg="white",
            font=("Segoe UI", escalar_fuente(11), "bold"), relief="flat", cursor="hand2",
            command=_reimprimir
        ).pack(side="left", fill="x", expand=True, padx=(0, 5), ipady=5)

    btn_cerrar = tk.Button(
        f_botones, text="✔️ Cerrar Recibo", bg="#28a745", fg="white",
        font=("Segoe UI", escalar_fuente(11), "bold"), relief="flat", cursor="hand2",
        command=top.destroy
    )
    btn_cerrar.pack(side="left", fill="x", expand=True, ipady=5)

    top.bind("<Return>", lambda e: top.destroy())
    top.bind("<Escape>", lambda e: top.destroy())
    top.focus_set()