

class POSNavegacionMixin:
    """Navegación con teclado y atajos del Punto de Venta.

    Métodos de ModuloPOS (ver pos_main.py). Antes se asignaban a mano
    a la clase, uno por uno, al final de aquel archivo.
    """

    def aplicar_resalte_focus(self, widget):
        # Dejamos que el estilo global de ventana_principal.py maneje el resaltado
        pass


    def aplicar_resalte_boton(self, boton, color_normal):
        boton.bind("<FocusIn>", lambda e: boton.config(
            bg=color_normal,
            highlightthickness=2,
            highlightbackground="#475569", # Un borde gris oscuro cuando tiene foco
            highlightcolor="#475569",
            bd=0
        ))

        boton.bind("<FocusOut>", lambda e: boton.config(
            bg=color_normal,
            highlightthickness=0,
            bd=0,
            relief="flat"
        ))


    def configurar_navegacion_libre(self):
        self.nav_widgets = [
            self.entry_busqueda,
            self.btn_buscar,
            self.entry_cantidad,
            self.entry_peso,
            self.btn_agregar,
            self.btn_mostrar_todo,
            self.btn_editar,
            self.btn_eliminar,
            self.btn_vaciar,
            self.entry_pago_cliente,
            self.btn_pago_efectivo,
            self.btn_pago_tarjeta,
            self.btn_pago_transfer,
            self.btn_cancelar,
            self.btn_cerrar
        ]

        self.nav_widgets = [w for w in self.nav_widgets if w is not None]

        for widget in self.nav_widgets:
            widget.bind("<Left>", lambda e, d="left": self.mover_foco_espacial(d))
            widget.bind("<Right>", lambda e, d="right": self.mover_foco_espacial(d))
            widget.bind("<Up>", lambda e, d="up": self.mover_foco_espacial(d))
            widget.bind("<Down>", lambda e, d="down": self.mover_foco_espacial(d))


    def centro_widget(self, widget):
        self.root.update_idletasks()
        x = widget.winfo_rootx()
        y = widget.winfo_rooty()
        w = widget.winfo_width()
        h = widget.winfo_height()
        return (x + w / 2, y + h / 2)


    def candidatos_direccion(self, actual, direccion):
        ax, ay = self.centro_widget(actual)
        candidatos = []

        for w in self.nav_widgets:
            if w == actual:
                continue
            if not w.winfo_ismapped():
                continue

            wx, wy = self.centro_widget(w)
            dx = wx - ax
            dy = wy - ay

            valido = False
            if direccion == "right" and dx > 10:
                valido = True
            elif direccion == "left" and dx < -10:
                valido = True
            elif direccion == "down" and dy > 10:
                valido = True
            elif direccion == "up" and dy < -10:
                valido = True

            if valido:
                distancia = (dx * dx + dy * dy) ** 0.5
                penalizacion = abs(dy) * 2.5 if direccion in ("right", "left") else abs(dx) * 2.5
                score = distancia + penalizacion
                candidatos.append((score, w))

        candidatos.sort(key=lambda x: x[0])
        return [w for _, w in candidatos]


    def mover_foco_espacial(self, direccion):
        actual = self.root.focus_get()

        if actual not in self.nav_widgets:
            if self.nav_widgets:
                self.nav_widgets[0].focus_set()
            return "break"

        candidatos = self.candidatos_direccion(actual, direccion)
        if candidatos:
            destino = candidatos[0]
            destino.focus_set()
            if hasattr(destino, "select_range"):
                destino.select_range(0, "end")
        return "break"


    def configurar_enter_campos(self):
        self.entry_busqueda.bind("<Return>", self.enter_en_busqueda)
        self.entry_cantidad.bind("<Return>", lambda e: self.focus_siguiente_desde_cantidad())
        self.entry_peso.bind("<Return>", lambda e: self.focus_siguiente_desde_peso())
        self.entry_pago_cliente.bind("<Return>", lambda e: self.confirmar_venta_ticket())

        for btn_name in ("btn_buscar", "btn_agregar", "btn_mostrar_todo", "btn_editar",
                         "btn_eliminar", "btn_vaciar", "btn_confirmar", "btn_cancelar",
                         "btn_cerrar", "btn_pago_efectivo", "btn_pago_tarjeta", "btn_pago_transfer"):
            btn = getattr(self, btn_name, None)
            if btn is not None:
                btn.bind("<Return>", lambda e, b=btn: b.invoke())



    def configurar_atajos_teclado(self):
        self.root.bind("<F2>", lambda e: self.confirmar_venta_ticket())
        self.root.bind("<F3>", lambda e: self.vaciar_ticket())
        self.root.bind("<F4>", lambda e: self.enfocar_busqueda())
        self.root.bind("<F5>", lambda e: self.mostrar_todos())
        self.root.bind("<F6>", lambda e: self.editar_linea_ticket())
        self.root.bind("<Delete>", lambda e: self.eliminar_linea_ticket())
        self.root.bind("<Escape>", lambda e: self.volver_menu())
        self.root.bind("<Control-b>", lambda e: self.enfocar_busqueda())
        self.root.bind("<Control-p>", lambda e: self.enfocar_pago())


    def liberar_atajos_teclado(self):
        """Libera todos los atajos de teclado del POS vinculados a root.

        Debe llamarse al salir del módulo para evitar que bindings huérfanos
        invoquen widgets ya destruidos (TclError) o sobreescriban atajos globales.
        """
        # Cancelar la búsqueda en espera: si se dispara después de cerrar el
        # módulo, intenta escribir en widgets que ya no existen.
        try:
            from .pos_ui import _cancelar_busqueda_pendiente
            _cancelar_busqueda_pendiente(self)
        except Exception:
            # SILENCIO DELIBERADO: no puede impedir salir del módulo.
            pass

        for tecla in ("<F2>", "<F3>", "<F4>", "<F5>", "<F6>",
                      "<Delete>", "<Escape>", "<Control-b>", "<Control-p>"):
            try:
                self.root.unbind(tecla)
            except Exception:
                # SILENCIO DELIBERADO: unbind falla si el atajo ya no estaba.
                pass
