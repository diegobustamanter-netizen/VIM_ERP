from tkinter import messagebox

from config import COLOR_GRIS

from .pos_ui import POSInterfazMixin
from .pos_busqueda import POSBusquedaMixin
from .pos_ticket import POSTicketMixin
from .pos_navegacion import POSNavegacionMixin
from .pos_utils import moneda


class ModuloPOS(POSInterfazMixin, POSBusquedaMixin, POSTicketMixin, POSNavegacionMixin):
    """Punto de Venta.

    El módulo está partido por responsabilidad y cada parte aporta sus
    métodos por herencia:

        pos_ui         -> POSInterfazMixin    (construcción de pantalla)
        pos_busqueda   -> POSBusquedaMixin    (buscar y seleccionar productos)
        pos_ticket     -> POSTicketMixin      (armar el ticket y cobrar)
        pos_navegacion -> POSNavegacionMixin  (teclado y atajos)

    Antes cada método se enganchaba a mano al final de este archivo
    (`ModuloPOS.buscar = pos_busqueda.buscar`, unas 45 líneas). Con Mixins
    los métodos nuevos quedan disponibles solos y las herramientas de
    desarrollo pueden seguir de dónde viene cada uno.
    """

    def __init__(self, root, frame_contenido, volver_menu):
        self.root = root
        self.frame_contenido = frame_contenido
        self._volver_menu_callback = volver_menu

        self.root.configure(bg=COLOR_GRIS)

        self.ticket = []

        self.entry_busqueda = None
        self.entry_cantidad = None
        self.entry_peso = None
        self.entry_pago_cliente = None

        self.tree_productos = None
        self.tree_ticket = None

        self.lbl_items = None
        self.lbl_total = None
        self.lbl_vuelto = None
        self.lbl_modo = None

        self.btn_buscar = None
        self.btn_agregar = None
        self.btn_mostrar_todo = None
        self.btn_editar = None
        self.btn_eliminar = None
        self.btn_vaciar = None
        self.btn_pago_efectivo = None
        self.btn_pago_tarjeta = None
        self.btn_pago_transfer = None
        self.btn_cancelar = None
        self.btn_cerrar = None

        self.nav_widgets = []

        # Temporizador de la búsqueda mientras se escribe (ver pos_ui)
        self._busqueda_after_id = None

        self.construir_interfaz()
        self.configurar_enter_campos()
        self.configurar_atajos_teclado()
        self.configurar_navegacion_libre()

        if self.entry_busqueda:
            self.entry_busqueda.focus_set()

    def volver_menu(self):
        """Libera atajos de teclado y luego vuelve al menú principal.

        Si hay líneas cargadas pide confirmación: al volver al menú el ticket
        se descarta, y un Esc accidental a mitad de una venta borraba todo
        sin aviso.
        """
        if self.ticket:
            total = self.calcular_total()
            confirmar = messagebox.askyesno(
                "Ticket en curso",
                f"Hay {len(self.ticket)} línea(s) sin cobrar por un total de "
                f"{moneda(total)}.\n\n"
                "Si vuelves al menú se perderá el ticket.\n\n"
                "¿Deseas salir de todas formas?",
                default="no",
                icon="warning",
                parent=self.root
            )
            if not confirmar:
                self.entry_busqueda.focus_set()
                return

        self.liberar_atajos_teclado()
        self._volver_menu_callback()


def abrir_modulo_pos(root, frame_contenido, volver_menu):
    return ModuloPOS(root, frame_contenido, volver_menu)
