from .ui import ConfiguracionUI

class ModuloConfiguracion:
    def __init__(self, root, frame_contenido, volver_menu):
        self.root = root
        self.frame_contenido = frame_contenido
        self.volver_menu = volver_menu
        
        # Instanciar el layout de la UI central
        self.ui = ConfiguracionUI(self.frame_contenido, self.cargar_seccion, self.volver_menu)
        
        # Iniciar directamente en 'empresa'
        self.ui.marcar_activo("empresa")
        self.cargar_seccion("empresa")
        
    def cargar_seccion(self, slug):
        """Callback que inyecta la vista requerida en el panel derecho."""
        self.ui.limpiar_panel_derecho()
        
        if slug == "empresa":
            from .secciones.empresa import EmpresaSeccion
            EmpresaSeccion(self.ui.panel_derecho, self.ui)
        elif slug == "finanzas":
            from .secciones.finanzas import FinanzasSeccion
            FinanzasSeccion(self.ui.panel_derecho, self.ui)
        elif slug == "sistema":
            from .secciones.sistema import SistemaSeccion
            SistemaSeccion(self.ui.panel_derecho, self.ui, root=self.root)
        elif slug == "acerca_de":
            from .secciones.acerca_de import AcercaDeSeccion
            AcercaDeSeccion(self.ui.panel_derecho, self.ui)

def abrir_modulo_configuracion(root, frame_contenido, volver_menu):
    ModuloConfiguracion(root, frame_contenido, volver_menu)
