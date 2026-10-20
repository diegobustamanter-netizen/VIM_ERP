from . import compras_ui

class ModuloCompras:
    def __init__(self, root, frame_contenido, volver_menu):
        self.root = root
        self.frame_contenido = frame_contenido
        self.volver_menu = volver_menu
        
    def abrir(self):
        compras_ui.construir_interfaz(self)

def abrir_modulo(root, frame_contenido, volver_menu):
    """Punto de entrada para la ventana principal."""
    modulo = ModuloCompras(root, frame_contenido, volver_menu)
    modulo.abrir()
