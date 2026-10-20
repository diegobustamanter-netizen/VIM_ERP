"""POS: la lógica del mostrador, probada sin abrir la interfaz.

Estas pruebas apuntan a la lógica pura (database.productos y
modulos.pos.pos_calculos), que no depende de tkinter. Lo que queda en
pos_ticket.py es solo pintar el resultado en los widgets.
"""

from base import PruebaVIM


class PruebaBusquedaPorCodigo(PruebaVIM):
    """El escaneo tiene que reconocer un código exacto."""

    def setUp(self):
        super().setUp()
        with self.conectar() as con:
            con.execute(
                """
                INSERT INTO productos (nombre, tipo_item, codigo_barras, codigo_pos,
                                       precio_compra, precio_venta, precio_por_kilo,
                                       stock, stock_minimo, tipo_venta, activo, fecha_creacion)
                VALUES ('Gaseosa 1.5L','producto','7801234567890','501',
                        500, 1200, 0, 50, 0, 'unidad', 1, ?)
                """,
                (self.ahora_local(),)
            )
            con.execute(
                """
                INSERT INTO productos (nombre, tipo_item, codigo_barras, codigo_pos,
                                       precio_compra, precio_venta, precio_por_kilo,
                                       stock, stock_minimo, tipo_venta, activo, fecha_creacion)
                VALUES ('Manzana granel','producto', NULL,'700',
                        800, 0, 1500, 30, 0, 'peso', 1, ?)
                """,
                (self.ahora_local(),)
            )
            con.commit()

        from database.productos import obtener_producto_por_codigo
        self.por_codigo = obtener_producto_por_codigo

    def test_encuentra_por_codigo_de_barras(self):
        prod = self.por_codigo("7801234567890")

        self.assertIsNotNone(prod, "No encontró el producto por código de barras")
        self.assertEqual(prod["nombre"], "Gaseosa 1.5L")

    def test_encuentra_por_codigo_pos(self):
        prod = self.por_codigo("501")

        self.assertIsNotNone(prod, "No encontró el producto por PLU")
        self.assertEqual(prod["nombre"], "Gaseosa 1.5L")

    def test_un_nombre_no_es_un_codigo(self):
        """Buscar por nombre debe seguir el camino largo, no el de escaneo."""
        self.assertIsNone(self.por_codigo("Gaseosa"))

    def test_texto_vacio_no_rompe(self):
        for valor in ("", "   ", None):
            with self.subTest(valor=valor):
                self.assertIsNone(self.por_codigo(valor))

    def test_un_codigo_inexistente_no_devuelve_cualquier_cosa(self):
        self.assertIsNone(self.por_codigo("0000000000000"))

    def test_los_productos_por_peso_se_reconocen_como_tales(self):
        """Con un producto por peso el POS no debe agregarlo solo:
        el cajero tiene que ingresar los kilos antes."""
        prod = self.por_codigo("700")

        self.assertIsNotNone(prod)
        self.assertEqual(prod["tipo_venta"], "peso")


class PruebaVueltoYFaltante(PruebaVIM):
    """El cajero tiene que ver cuánto falta, no un cero engañoso."""

    def _estado(self, total, pago):
        from modulos.pos.pos_calculos import estado_del_pago
        return estado_del_pago(total, pago)

    def test_pago_de_mas_muestra_vuelto(self):
        e = self._estado(total=10000, pago=15000)

        self.assertEqual(e["titulo"], "VUELTO")
        self.assertEqual(e["monto"], 5000)
        self.assertFalse(e["falta"])

    def test_pago_justo_no_es_faltante(self):
        e = self._estado(total=10000, pago=10000)

        self.assertEqual(e["titulo"], "VUELTO")
        self.assertEqual(e["monto"], 0)
        self.assertFalse(e["falta"])

    def test_pago_insuficiente_muestra_cuanto_falta(self):
        e = self._estado(total=10000, pago=8500)

        self.assertEqual(e["titulo"], "FALTA",
                         "Debería avisar que falta plata, no mostrar vuelto")
        self.assertEqual(e["monto"], 1500,
                         "Tiene que decir cuánto falta exactamente")
        self.assertTrue(e["falta"])

    def test_el_faltante_se_ve_en_rojo(self):
        from modulos.pos.pos_calculos import ROJO_TEXTO, VERDE_TEXTO

        self.assertEqual(self._estado(10000, 8500)["color"], ROJO_TEXTO)
        self.assertEqual(self._estado(10000, 15000)["color"], VERDE_TEXTO)

    def test_sin_pago_ingresado_no_alarma(self):
        """Con el campo vacío el cliente todavía no entregó nada."""
        e = self._estado(total=10000, pago=0)

        self.assertEqual(e["titulo"], "VUELTO")
        self.assertFalse(e["falta"], "No hay nada que reclamar todavía")

    def test_ticket_vacio_no_rompe(self):
        e = self._estado(total=0, pago=0)
        self.assertEqual(e["monto"], 0)
        self.assertFalse(e["falta"])

    def test_valores_invalidos_no_rompen(self):
        """El campo de pago es texto libre: puede llegar cualquier cosa."""
        for total, pago in [(None, None), ("abc", "def"), (10000, None)]:
            with self.subTest(total=total, pago=pago):
                e = self._estado(total, pago)
                self.assertIn(e["titulo"], ("VUELTO", "FALTA"))
                self.assertGreaterEqual(e["monto"], 0)


class PruebaGraciaEnElTicket(PruebaVIM):
    """La ventana de gracia del ticket es independiente de la de productos."""

    def setUp(self):
        super().setUp()
        from modulos.seguridad.sesion import Sesion
        self.Sesion = Sesion
        Sesion.iniciar({"id": 1, "nombre": "Prueba", "rol": "administrador"})

    def tearDown(self):
        self.Sesion.cerrar()
        super().tearDown()

    def test_autorizar_el_ticket_no_habilita_borrar_productos(self):
        self.Sesion.registrar_autorizacion("eliminar_linea_ticket")

        self.assertTrue(self.Sesion.autorizacion_vigente("eliminar_linea_ticket", 60))
        self.assertFalse(
            self.Sesion.autorizacion_vigente("eliminar_producto", 60),
            "Autorizar el ticket habilitó borrar productos del catálogo")

    def test_autorizar_productos_no_habilita_el_ticket(self):
        self.Sesion.registrar_autorizacion("eliminar_producto")

        self.assertFalse(
            self.Sesion.autorizacion_vigente("eliminar_linea_ticket", 60),
            "Autorizar el catálogo habilitó tocar el ticket")
