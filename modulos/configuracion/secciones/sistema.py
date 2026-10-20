from modulos.backup.backup_main import ModuloBackup


class SistemaSeccion:
    """
    Sección de Sistema/Backup embebida en Configuración.
    Delega toda la funcionalidad a ModuloBackup en modo embebido
    para evitar duplicación de código.
    """

    def __init__(self, parent, ui, root=None):
        self.parent = parent
        self.ui = ui
        # Modo embebido: sin header propio, sin botón volver
        self.backup = ModuloBackup(
            root or parent.winfo_toplevel(),
            parent,
            volver_menu=None,
            embebido=True
        )
