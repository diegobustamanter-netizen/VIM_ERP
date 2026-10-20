"""Que ModuloPOS tenga de verdad todo lo que su propio código usa.

Este archivo existe por un error real: en el POS se agregó el método
`producto_por_codigo_exacto` al mixin de búsqueda, pero no se lo enganchó a
ModuloPOS (que en ese momento recibía sus métodos uno por uno, asignados a
mano). El código llamaba a `self.producto_por_codigo_exacto(...)` y habría
reventado con AttributeError al primer Enter en el buscador.

El análisis es estático (se lee el código, no se ejecuta), así que corre sin
necesidad de tkinter ni de abrir ninguna ventana.
"""

import ast
import os
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARPETA_POS = os.path.join(RAIZ, "modulos", "pos")

# Heredados de object o provistos por el entorno, no por el código del POS
PERMITIDOS = {"__init__", "__class__"}


def _arboles():
    for nombre in sorted(os.listdir(CARPETA_POS)):
        if nombre.endswith(".py"):
            ruta = os.path.join(CARPETA_POS, nombre)
            with open(ruta, encoding="utf-8") as f:
                yield nombre, ast.parse(f.read())


class PruebaCableadoDelPOS(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.disponibles = set(PERMITIDOS)
        cls.usados = {}          # nombre -> (archivo, linea)

        for archivo, arbol in _arboles():
            for nodo in ast.walk(arbol):
                # Todo lo que definen las clases del paquete (los mixins y
                # ModuloPOS terminan aportando sus métodos por herencia)
                if isinstance(nodo, ast.ClassDef):
                    for h in nodo.body:
                        if isinstance(h, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            cls.disponibles.add(h.name)
                        elif isinstance(h, ast.Assign):
                            for t in h.targets:
                                if isinstance(t, ast.Name):
                                    cls.disponibles.add(t.id)

                # Atributos de instancia: self.algo = ...
                if isinstance(nodo, ast.Assign):
                    for t in nodo.targets:
                        if (isinstance(t, ast.Attribute)
                                and isinstance(t.value, ast.Name)
                                and t.value.id == "self"):
                            cls.disponibles.add(t.attr)

                # Llamadas self.algo(...)
                if (isinstance(nodo, ast.Call)
                        and isinstance(nodo.func, ast.Attribute)
                        and isinstance(nodo.func.value, ast.Name)
                        and nodo.func.value.id == "self"):
                    cls.usados.setdefault(
                        nodo.func.attr, (archivo, nodo.func.lineno))

    def test_todo_lo_que_el_pos_llama_existe(self):
        """Ningún self.metodo() puede quedar sin definir en ninguna parte."""
        faltantes = {
            nombre: origen
            for nombre, origen in self.usados.items()
            if nombre not in self.disponibles
        }

        if faltantes:
            detalle = "\n".join(
                f"  self.{n}()  -> usado en {a}:{l} pero no está definido"
                for n, (a, l) in sorted(faltantes.items())
            )
            self.fail(
                "El POS llama a métodos que no existen "
                f"(reventaría con AttributeError):\n{detalle}")

    def test_el_metodo_del_escaneo_esta_disponible(self):
        """Caso concreto que ya falló una vez."""
        self.assertIn("producto_por_codigo_exacto", self.disponibles)

    def test_modulo_pos_hereda_de_los_cuatro_mixins(self):
        """Si alguien saca un mixin, media pantalla deja de funcionar."""
        ruta = os.path.join(CARPETA_POS, "pos_main.py")
        with open(ruta, encoding="utf-8") as f:
            arbol = ast.parse(f.read())

        bases = []
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.ClassDef) and nodo.name == "ModuloPOS":
                bases = [b.id for b in nodo.bases if isinstance(b, ast.Name)]

        for mixin in ("POSInterfazMixin", "POSBusquedaMixin",
                      "POSTicketMixin", "POSNavegacionMixin"):
            self.assertIn(mixin, bases, f"ModuloPOS ya no hereda de {mixin}")

    def test_la_lista_de_productos_se_repuebla_tras_agregar(self):
        """Al agregar un producto, el catálogo NO puede quedar vacío.

        Pasó de verdad: se quitó la recarga del catálogo para ahorrar una
        consulta y la lista quedaba en blanco después de cada producto. Desde
        el mostrador se ve como si se hubieran borrado todos los productos.
        """
        ruta = os.path.join(CARPETA_POS, "pos_ticket.py")
        with open(ruta, encoding="utf-8") as f:
            arbol = ast.parse(f.read())
            f.seek(0)
            fuente = f.read()

        fn = None
        for nodo in ast.walk(arbol):
            if (isinstance(nodo, ast.FunctionDef)
                    and nodo.name == "limpiar_campos_entrada_producto"):
                fn = ast.get_source_segment(fuente, nodo)

        self.assertIsNotNone(fn, "No existe limpiar_campos_entrada_producto")
        self.assertIn(
            "self.mostrar_todos()", fn,
            "Tras agregar un producto la lista queda vacía: hay que repoblarla")

    def test_no_quedan_metodos_asignados_a_mano(self):
        """El enganche manual es justo lo que dejaba pasar métodos sin conectar."""
        ruta = os.path.join(CARPETA_POS, "pos_main.py")
        with open(ruta, encoding="utf-8") as f:
            arbol = ast.parse(f.read())

        asignados = [
            t.attr
            for nodo in arbol.body if isinstance(nodo, ast.Assign)
            for t in nodo.targets
            if isinstance(t, ast.Attribute)
            and isinstance(t.value, ast.Name) and t.value.id == "ModuloPOS"
        ]

        self.assertEqual(asignados, [],
                         "Volvieron las asignaciones manuales a ModuloPOS")


if __name__ == "__main__":
    unittest.main()
