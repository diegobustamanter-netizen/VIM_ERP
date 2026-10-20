"""Armado del Centro de Descargas.

Este archivo existe por un problema concreto: el botón "DESCARGAR REPORTE"
se empaquetaba DESPUÉS del área desplazable, que usa expand=True. Tk reparte
el espacio en orden, así que para cuando llegaba el botón ya no quedaba nada
y desaparecía de la vista. Además la ventana era de tamaño fijo, sin forma de
agrandarla cuando el contenido no entraba.

Se revisa el código sin abrirlo, así que corre sin tkinter.
"""

import ast
import os
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENTAS_MAIN = os.path.join(RAIZ, "modulos", "ventas_reportes", "ventas_main.py")


class PruebaArmadoCentroDescargas(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(VENTAS_MAIN, encoding="utf-8") as f:
            cls.fuente = f.read()
        arbol = ast.parse(cls.fuente)

        cls.modal = None
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.FunctionDef) and nodo.name == "abrir_modal_exportacion":
                cls.modal = ast.get_source_segment(cls.fuente, nodo)
        assert cls.modal, "No se encontró abrir_modal_exportacion"

    def _linea_de(self, texto):
        """Posición de un fragmento dentro del modal (para comparar orden)."""
        pos = self.modal.find(texto)
        self.assertNotEqual(pos, -1, f"No se encontró '{texto}' en el modal")
        return pos

    # ------------------------------------------------------------------

    def test_la_ventana_es_ajustable(self):
        self.assertIn("top.resizable(True, True)", self.modal,
                      "La ventana volvió a quedar de tamaño fijo")

    def test_tiene_tamano_minimo(self):
        self.assertIn("top.minsize(", self.modal,
                      "Sin minsize se puede achicar hasta ocultar todo")

    def test_el_minimo_no_supera_lo_que_entra_en_pantalla(self):
        """Un minsize mayor al área útil deja la ventana fuera de la vista."""
        self.assertIn("min(escalar(560), top.winfo_width())", self.modal)

    def test_el_pie_se_reserva_antes_del_cuerpo(self):
        """LO IMPORTANTE: si el cuerpo expande primero, el botón desaparece."""
        pos_pie = self._linea_de('pie.pack(side="bottom"')
        pos_cuerpo = self._linea_de("preparar_modal_scrollable(top")

        self.assertLess(pos_pie, pos_cuerpo,
                        "El pie debe empaquetarse ANTES del área desplazable, "
                        "si no Tk le deja sin espacio al botón")

    def test_el_boton_vive_en_el_pie(self):
        self.assertIn("pie, text=\"📥  DESCARGAR REPORTE\"", self.modal,
                      "El botón volvió a colgarse de la ventana en vez del pie")

    def test_las_descripciones_se_reajustan_al_ancho(self):
        """Con wraplength fijo el texto se cortaba a los costados."""
        self.assertIn("etiquetas_ajustables", self.modal)
        self.assertIn('cuerpo.bind("<Configure>", _reajustar_textos)', self.modal)

    def test_los_atajos_se_reparten_en_dos_filas(self):
        """Seis botones en una fila no entran con la ventana angosta."""
        self.assertIn("fila_atajos_1", self.modal)
        self.assertIn("fila_atajos_2", self.modal)

    def test_el_encabezado_va_arriba_de_todo(self):
        pos_header = self._linea_de('header.pack(side="top"')
        pos_cuerpo = self._linea_de("preparar_modal_scrollable(top")

        self.assertLess(pos_header, pos_cuerpo)

    def test_el_boton_no_usa_side_bottom_sobre_la_ventana(self):
        """Ese era exactamente el empaquetado que lo hacía desaparecer."""
        self.assertNotIn('btn_exp.pack(side="bottom"', self.modal)


if __name__ == "__main__":
    unittest.main()
