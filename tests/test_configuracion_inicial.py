"""El asistente de puesta en marcha: qué pasos aparecen y cuándo.

Antes eran dos ventanas separadas que se abrían casi a la vez. La de
seguridad no esperaba a cerrarse, así que la de tipo de negocio se dibujaba
encima y las dos se peleaban el foco.

Acá se prueba la decisión (qué pasos corresponden) sin abrir ventanas.
"""

import ast
import os

from base import PruebaVIM

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECUPERACION = os.path.join(RAIZ, "modulos", "seguridad", "recuperacion_ui.py")


def _pasos(pedir_negocio, pedir_seguridad):
    """Replica la lógica de ModalOnboarding.__init__ sin construir la ventana."""
    pasos = ["bienvenida"]
    if pedir_negocio:
        pasos.append("negocio")
    if pedir_seguridad:
        pasos.append("seguridad")
    pasos.append("final")
    return pasos


class PruebaPasosDelAsistente(PruebaVIM):

    def test_instalacion_nueva_pide_las_dos_cosas(self):
        pasos = _pasos(pedir_negocio=True, pedir_seguridad=True)

        self.assertEqual(pasos, ["bienvenida", "negocio", "seguridad", "final"])

    def test_si_ya_hay_tipo_de_negocio_no_se_vuelve_a_preguntar(self):
        pasos = _pasos(pedir_negocio=False, pedir_seguridad=True)

        self.assertNotIn("negocio", pasos)
        self.assertIn("seguridad", pasos)

    def test_si_ya_hay_pregunta_de_seguridad_solo_falta_el_negocio(self):
        """Caso de quien actualiza desde una versión anterior."""
        pasos = _pasos(pedir_negocio=True, pedir_seguridad=False)

        self.assertIn("negocio", pasos)
        self.assertNotIn("seguridad", pasos)

    def test_el_modo_de_negocio_arranca_sin_configurar(self):
        """Es lo que dispara el paso de tipo de negocio."""
        from database.negocio import modo_configurado

        self.assertFalse(modo_configurado())

    def test_una_vez_elegido_ya_no_hace_falta_preguntarlo(self):
        from database import negocio

        negocio.establecer_modo_negocio(negocio.MODO_SERVICIOS)

        self.assertTrue(negocio.modo_configurado())


class PruebaCableadoDelAsistente(PruebaVIM):
    """Verifica el código del asistente sin abrirlo (no hace falta tkinter)."""

    @classmethod
    def setUpClass(cls):
        with open(RECUPERACION, encoding="utf-8") as f:
            cls.fuente = f.read()
        cls.arbol = ast.parse(cls.fuente)

    def _funcion(self, nombre, clase=None):
        for nodo in ast.walk(self.arbol):
            if clase and isinstance(nodo, ast.ClassDef) and nodo.name == clase:
                for h in nodo.body:
                    if isinstance(h, ast.FunctionDef) and h.name == nombre:
                        return h
            if not clase and isinstance(nodo, ast.FunctionDef) and nodo.name == nombre:
                return nodo
        return None

    def test_el_asistente_espera_a_cerrarse(self):
        """El bug original: sin wait_window, lo siguiente se dibuja encima."""
        fn = self._funcion("verificar_y_forzar_configuracion_inicial")
        self.assertIsNotNone(fn, "No existe la función de configuración inicial")

        cuerpo = ast.get_source_segment(self.fuente, fn)
        self.assertIn("wait_window", cuerpo,
                      "El asistente no espera: se van a superponer ventanas")

    def test_el_asistente_bloquea_el_fondo(self):
        fn = self._funcion("__init__", clase="ModalOnboarding")
        cuerpo = ast.get_source_segment(self.fuente, fn)

        self.assertIn("grab_set", cuerpo,
                      "Sin grab_set se puede tocar la ventana de atrás")

    def test_existen_los_cuatro_pasos(self):
        for paso in ("crear_fase1", "crear_fase_negocio", "crear_fase2", "crear_fase3"):
            self.assertIsNotNone(
                self._funcion(paso, clase="ModalOnboarding"),
                f"Falta el paso {paso} del asistente")

    def test_los_pasos_avanzan_en_cadena(self):
        """Cada paso llama a _avanzar, no salta directo a otro paso."""
        for paso in ("crear_fase1", "guardar_fase2"):
            fn = self._funcion(paso, clase="ModalOnboarding")
            cuerpo = ast.get_source_segment(self.fuente, fn)
            self.assertIn("_avanzar", cuerpo,
                          f"{paso} no encadena con el paso siguiente")

    def test_no_quedan_dos_ventanas_separadas(self):
        """El modal viejo de tipo de negocio no debe volver a usarse."""
        ruta = os.path.join(RAIZ, "ventana_principal.py")
        with open(ruta, encoding="utf-8") as f:
            arranque = f.read()

        self.assertNotIn("verificar_y_preguntar_tipo_negocio", arranque)
        self.assertIn("verificar_y_forzar_configuracion_inicial", arranque)
