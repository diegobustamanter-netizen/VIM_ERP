"""Ventas: precios, stock y folios.

Todo lo que toca plata directamente.
"""

import threading

from base import PruebaVIM


class PruebaPrecios(PruebaVIM):
    """El precio que se cobra tiene que ser el que queda registrado."""

    def setUp(self):
        super().setUp()
        self.abrir_caja()
        self.configurar_iva(0)
        self.pid = self.crear_producto(precio_venta=1000, precio_compra=400, stock=100)

    def _precio_registrado(self, venta_id):
        with self.conectar() as con:
            return con.execute(
                "SELECT precio_unitario FROM detalle_ventas WHERE venta_id = ?",
                (venta_id,)
            ).fetchone()["precio_unitario"]

    def test_precio_modificado_y_autorizado_llega_a_la_base(self):
        """Con autorización de admin, el precio del ticket manda.

        Antes se descartaba y la venta quedaba con el precio de catálogo: el
        cliente veía un recibo y el sistema registraba otra cosa.
        """
        from database.ventas import confirmar_venta

        ok, msg, venta_id = confirmar_venta(
            [self.linea_ticket(self.pid, cantidad=2, precio_unitario=111,
                               precio_modificado=True)],
            999999, "efectivo", usuario_id=1)

        self.assertTrue(ok, msg)
        self.assertEqual(self._precio_registrado(venta_id), 111)

    def test_precio_sin_autorizar_no_se_respeta(self):
        """Sin la marca de autorización manda el catálogo.

        Protege contra inyectar precios armando la línea a mano.
        """
        from database.ventas import confirmar_venta

        ok, msg, venta_id = confirmar_venta(
            [self.linea_ticket(self.pid, cantidad=1, precio_unitario=999999)],
            999999, "efectivo", usuario_id=1)

        self.assertTrue(ok, msg)
        self.assertEqual(self._precio_registrado(venta_id), 1000,
                         "Se coló un precio que nadie autorizó")

    def test_precio_negativo_se_rechaza(self):
        """Un precio negativo generaría una venta que devuelve plata."""
        from database.ventas import confirmar_venta

        ok, _, venta_id = confirmar_venta(
            [self.linea_ticket(self.pid, cantidad=1, precio_unitario=-500,
                               precio_modificado=True)],
            999999, "efectivo", usuario_id=1)

        self.assertFalse(ok, "Se aceptó un precio negativo")
        self.assertIsNone(venta_id)

    def test_el_precio_modificado_queda_en_el_historial(self):
        """Cambiar un precio tiene que dejar rastro para auditoría."""
        from database.ventas import confirmar_venta

        ok, msg, venta_id = confirmar_venta(
            [self.linea_ticket(self.pid, cantidad=1, precio_unitario=111,
                               precio_modificado=True)],
            999999, "efectivo", usuario_id=1)
        self.assertTrue(ok, msg)

        with self.conectar() as con:
            detalle = con.execute(
                "SELECT detalles FROM historial WHERE tabla='ventas' AND referencia_id=?",
                (venta_id,)
            ).fetchone()["detalles"]

        self.assertIn("Precios modificados", detalle)


class PruebaStock(PruebaVIM):

    def setUp(self):
        super().setUp()
        self.abrir_caja()
        self.configurar_iva(0)

    def test_no_se_puede_vender_mas_de_lo_que_hay(self):
        from database.ventas import confirmar_venta

        pid = self.crear_producto(precio_venta=1000, stock=5)
        ok, msg, _ = confirmar_venta(
            [self.linea_ticket(pid, cantidad=10, precio_unitario=1000)],
            999999, "efectivo", usuario_id=1)

        self.assertFalse(ok, "Se vendió stock inexistente")
        self.assertIn("stock", msg.lower())

    def test_la_venta_descuenta_el_stock(self):
        from database.ventas import confirmar_venta

        pid = self.crear_producto(precio_venta=1000, stock=10)
        ok, msg, _ = confirmar_venta(
            [self.linea_ticket(pid, cantidad=3, precio_unitario=1000)],
            999999, "efectivo", usuario_id=1)
        self.assertTrue(ok, msg)

        with self.conectar() as con:
            stock = con.execute("SELECT stock FROM productos WHERE id=?", (pid,)).fetchone()["stock"]
        self.assertEqual(stock, 7)

    def test_un_servicio_se_vende_sin_stock(self):
        """Un corte de pelo no se inventaría: no debe frenar por stock."""
        from database.ventas import confirmar_venta

        pid = self.crear_producto(precio_venta=8000, stock=0, tipo_item="servicio")
        ok, msg, _ = confirmar_venta(
            [self.linea_ticket(pid, cantidad=3, precio_unitario=8000,
                               tipo_item="servicio")],
            999999, "efectivo", usuario_id=1)

        self.assertTrue(ok, f"Un servicio no debería frenar por stock: {msg}")

    def test_sin_caja_abierta_no_se_puede_vender(self):
        from database.ventas import confirmar_venta

        with self.conectar() as con:
            con.execute("UPDATE cajas_sesiones SET estado = 'cerrada'")
            con.commit()

        pid = self.crear_producto(precio_venta=1000, stock=10)
        ok, msg, _ = confirmar_venta(
            [self.linea_ticket(pid, cantidad=1, precio_unitario=1000)],
            999999, "efectivo", usuario_id=1)

        self.assertFalse(ok)
        self.assertIn("caja", msg.lower())


class PruebaFolios(PruebaVIM):
    """El folio identifica la venta: no puede repetirse ni fallar."""

    def setUp(self):
        super().setUp()
        self.abrir_caja()
        self.configurar_iva(0)
        self.pid = self.crear_producto(precio_venta=1000, stock=100000)

    def _vender(self):
        from database.ventas import confirmar_venta
        return confirmar_venta(
            [self.linea_ticket(self.pid, cantidad=1, precio_unitario=1000)],
            999999, "efectivo", usuario_id=1)

    def _folios(self):
        with self.conectar() as con:
            return [f["folio"] for f in con.execute("SELECT folio FROM ventas ORDER BY id")]

    def test_ventas_seguidas_no_chocan(self):
        """Cinco ventas sin pausa: antes la segunda moría por folio repetido."""
        for i in range(5):
            ok, msg, _ = self._vender()
            self.assertTrue(ok, f"Venta {i + 1} falló: {msg}")

        folios = self._folios()
        self.assertEqual(len(folios), 5)
        self.assertEqual(len(set(folios)), 5, "Hay folios repetidos")

    def test_el_correlativo_es_consecutivo(self):
        from database.ventas import _numero_de_folio

        for _ in range(3):
            self._vender()

        numeros = [_numero_de_folio(f) for f in self._folios()]
        self.assertEqual(numeros, [1, 2, 3])

    def test_ventas_simultaneas_no_repiten_folio(self):
        """Dos cajas vendiendo al mismo tiempo sobre la misma base."""
        cantidad = 8
        barrera = threading.Barrier(cantidad)
        resultados = []

        def vender():
            barrera.wait()          # que arranquen todos juntos de verdad
            resultados.append(self._vender())

        hilos = [threading.Thread(target=vender) for _ in range(cantidad)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()

        fallidas = [msg for ok, msg, _ in resultados if not ok]
        self.assertEqual(fallidas, [], f"Ventas rechazadas: {fallidas}")

        folios = self._folios()
        self.assertEqual(len(folios), len(set(folios)),
                         "Se repitió un folio bajo concurrencia")

    def test_folios_del_formato_viejo_no_interfieren(self):
        """Las ventas registradas antes del cambio conservan su folio."""
        from database.ventas import generar_folio_venta
        from database.utils import ahora

        hoy = ahora("%Y%m%d")
        with self.conectar() as con:
            con.execute(
                """
                INSERT INTO ventas (folio,tipo_documento,fecha,usuario_id,caja_sesion_id,
                                    subtotal,descuento,impuesto,total,monto_pagado,vuelto,
                                    metodo_pago,estado)
                VALUES (?,'boleta',?,1,1,100,0,0,100,100,0,'efectivo','completada')
                """,
                (f"VTA-{hoy}235959", self.ahora_local()),
            )
            con.commit()

        nuevo = generar_folio_venta()
        self.assertTrue(nuevo.startswith(f"VTA-{hoy}-"))
        self.assertNotEqual(nuevo, f"VTA-{hoy}235959")

    def test_folios_corruptos_no_rompen_el_correlativo(self):
        from database.ventas import _numero_de_folio

        for valor, esperado in [("VTA-20260101-0042", 42), ("VTA-20260101-9999", 9999),
                                ("VTA-20260101-abc", 0), ("roto", 0), (None, 0)]:
            with self.subTest(folio=valor):
                self.assertEqual(_numero_de_folio(valor), esperado)
