"""Pruebas de la anulación de ventas.

Qué se cuida:
  - Anular devuelve el stock y deja constancia del dinero devuelto en caja.
  - Anular dos veces la misma venta NO devuelve el stock dos veces.
  - Si la caja de la venta ya se cerró, el dinero sale de la caja abierta.
  - Si no hay ninguna caja abierta, no se anula nada (ni stock ni estado).
"""

from base import PruebaVIM


class PruebasAnulacion(PruebaVIM):

    def _vender(self, cantidad=3, precio=1000, stock=10):
        from database.ventas import confirmar_venta

        pid = self.crear_producto(precio_venta=precio, precio_compra=400, stock=stock)
        ok, msg, venta_id = confirmar_venta(
            [self.linea_ticket(pid, cantidad=cantidad, precio_unitario=precio)],
            999999, "efectivo", usuario_id=1)
        self.assertTrue(ok, msg)
        return pid, venta_id

    def _stock(self, pid):
        with self.conectar() as con:
            return con.execute("SELECT stock FROM productos WHERE id = ?", (pid,)).fetchone()[0]

    def _estado(self, venta_id):
        with self.conectar() as con:
            return con.execute("SELECT estado FROM ventas WHERE id = ?", (venta_id,)).fetchone()[0]

    def _egresos_anulacion(self, caja_id):
        with self.conectar() as con:
            return con.execute(
                "SELECT COALESCE(SUM(monto), 0) FROM movimientos_caja "
                "WHERE caja_sesion_id = ? AND categoria = 'anulación'", (caja_id,)
            ).fetchone()[0]

    def test_anular_devuelve_stock_y_registra_egreso(self):
        caja = self.abrir_caja()
        pid, venta_id = self._vender(cantidad=3, precio=1000, stock=10)
        self.assertEqual(self._stock(pid), 7)

        from database.ventas import anular_venta
        ok, msg = anular_venta(venta_id, usuario_id=1, motivo="Prueba")

        self.assertTrue(ok, msg)
        self.assertEqual(self._stock(pid), 10)
        self.assertEqual(self._estado(venta_id), "anulada")
        self.assertEqual(self._egresos_anulacion(caja), 3000)

    def test_anular_dos_veces_no_devuelve_stock_dos_veces(self):
        self.abrir_caja()
        pid, venta_id = self._vender(cantidad=3, stock=10)

        from database.ventas import anular_venta
        ok1, _ = anular_venta(venta_id, usuario_id=1)
        ok2, msg2 = anular_venta(venta_id, usuario_id=1)

        self.assertTrue(ok1)
        self.assertFalse(ok2, "La segunda anulación debió rechazarse")
        self.assertEqual(self._stock(pid), 10, "El stock se devolvió dos veces")

    def test_sin_caja_abierta_no_se_anula_nada(self):
        from database.caja import cerrar_caja
        caja = self.abrir_caja()
        pid, venta_id = self._vender(cantidad=3, stock=10)
        cerrar_caja(caja, 0, usuario_id=1)

        from database.ventas import anular_venta
        ok, msg = anular_venta(venta_id, usuario_id=1)

        self.assertFalse(ok)
        self.assertIn("caja", msg.lower())
        self.assertEqual(self._stock(pid), 7, "Se tocó el stock aunque no se anuló")
        self.assertEqual(self._estado(venta_id), "completada")

    def test_caja_cerrada_el_dinero_sale_de_la_caja_abierta(self):
        from database.caja import cerrar_caja
        caja_vieja = self.abrir_caja()
        pid, venta_id = self._vender(cantidad=2, precio=1500, stock=10)
        cerrar_caja(caja_vieja, 0, usuario_id=1)
        caja_nueva = self.abrir_caja()

        from database.ventas import anular_venta
        ok, msg = anular_venta(venta_id, usuario_id=1)

        self.assertTrue(ok, msg)
        self.assertEqual(self._egresos_anulacion(caja_nueva), 3000)
        self.assertEqual(self._egresos_anulacion(caja_vieja), 0,
                         "No se debe alterar una caja ya cerrada")
        self.assertEqual(self._stock(pid), 10)


if __name__ == "__main__":
    import unittest
    unittest.main()
